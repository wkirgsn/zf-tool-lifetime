import pandas as pd
import numpy as np
import pathlib
from os.path import join


class DataManager:
    time_format = '%b %y'

    def __init__(self):

        data_path = join(str(pathlib.Path(__file__).parent.resolve()),
                         '..', 'data')
        self.bedarf_formen = pd.read_csv(
            join(data_path, 'formen_und_giesszellenbedarf_2019.csv'))

        prod_form_lut = pd.read_csv(
            join(data_path, 'zuweisung_produkte_und_formen.csv'),
            dtype=dict(Produktnummer=np.uint32))
        bestellungen_2019 = \
            pd.read_csv(join(data_path, 'bestellungen_2019.csv')).dropna() \
                .reset_index(drop=True).astype(np.uint32)
        bestellungen_2020 = pd.read_csv(join(data_path,
                                             'bestellungen_2020.csv')).dropna() \
            .reset_index(drop=True).astype(np.uint32)

        self.orders_df = pd.concat([self._prettify_orders(bestellungen_2019),
                                    self._prettify_orders(bestellungen_2020)])
        prod = prod_form_lut.pop('Produktnummer')
        stacked_lut = (prod_form_lut
                       .stack()
                       .reset_index(1)
                       .rename(columns={'level_1': 'Form',
                                        0: 'Bedarf'}))
        self.forms_per_prod_df = (stacked_lut
                                  .join(prod)
                                  .reset_index(drop=True)
                                  .loc[:, ['Produktnummer', 'Form', 'Bedarf']])

        # calculate additional features
        self.attrition_by_product = \
            self.orders_df.Produktnummer.map(
                self.forms_per_prod_df[['Produktnummer', 'Bedarf']]
                    .groupby('Produktnummer').sum().Bedarf.to_dict())
        self.orders_df['total_attrition'] = \
            self.orders_df.amt_orders * self.attrition_by_product

        unique_forms = self.unique_forms
        self.prod_form_map = \
            self.forms_per_prod_df.pivot(index='Produktnummer', columns='Form',
                                         values='Bedarf')[unique_forms]
        self.prod_giesszellenbedarf_map = self.prod_form_map * \
                                          self.bedarf_formen['Gießzellenbedarf']\
                                          .values.T
        # prod_form_map.loc[56, 'F6']
        orders_x_forms_df = self.orders_df.merge(self.prod_form_map.reset_index(),
                                                 how='left', on='Produktnummer')
        # calculate form attritions over time

        orders_x_forms_df.loc[:, unique_forms] = \
            orders_x_forms_df.loc[:, unique_forms] * \
            orders_x_forms_df.amt_orders.values[:, np.newaxis]
        self.form_attritions_over_time = (orders_x_forms_df
                                          .groupby(['date'])[unique_forms]
                                          .sum())
        # sort by datetime_index
        self.form_attritions_over_time = (self.form_attritions_over_time
                                          .loc[pd.to_datetime(
            self.form_attritions_over_time.index, format=self.time_format)
                                         .sort_values()
                                         .strftime(self.time_format), :])

        # calculate next maintenance dates for each form
        duration_left = self.bedarf_formen['Anzahl maximaler Gießvorgänge'] - \
                        self.bedarf_formen['Anzahl bisheriger Gießvorgänge']
        next_attritions = self.form_attritions_over_time.loc[self.today:,
                          :].cumsum()
        maintenance = (next_attritions - duration_left.values[np.newaxis, :]) < 0
        next_maintenance = maintenance.sum()
        self.bedarf_formen['next maintenance'] = next_attritions.index[
                                                  next_maintenance.clip(upper=
                                                    len(maintenance) - 1)]

    @property
    def unique_forms(self):
        return self.bedarf_formen.Form.unique().tolist()

    @property
    def today(self):
        return pd.to_datetime('today').strftime(self.time_format)

    @property
    def avg_attrition(self):
        return self.relative_attritions_per_form.mean()

    @property
    def relative_attritions_per_form(self):
        forms = self.bedarf_formen.set_index('Form')
        amt_max = forms['Anzahl maximaler Gießvorgänge']
        amt_act = forms['Anzahl bisheriger Gießvorgänge']
        return (amt_max - amt_act) / amt_max

    @staticmethod
    def _prettify_orders(df):
        df.drop('Gesamt', axis=1, inplace=True)
        customer_x_prod = df.iloc[:, :2]
        orders = df.iloc[:, 2:].stack().reset_index(1)
        orders.columns = ['date', 'amt_orders']
        orders = orders.join(customer_x_prod)
        orders.date = pd.to_datetime(orders.date,
                                     format='%b-%y').dt.strftime('%b %y')
        return orders

    def maintenances_in_next_months(self, items_to_show=6):
        next_maintenances = self.bedarf_formen['next maintenance']
        dates = pd.to_datetime(next_maintenances, format=self.time_format)\
                                .sort_values().iloc[:items_to_show]
        forms = self.bedarf_formen.loc[dates.index, 'Form']
        maintenances = [f'Form {form:>14}: {date:<10}' for form, date in
                        zip(forms.tolist(),
                            dates.dt.strftime(self.time_format).tolist())]
        return maintenances

    def next_maintenance(self, _form):
        return self.bedarf_formen.loc[self.bedarf_formen.Form == _form,
                                      'next maintenance'].values[0]

    def maintenance_of_form_within_months(self, form, months=3):
        next_maintenance = pd.to_datetime(self.next_maintenance(form),
                                          format=self.time_format)
        return next_maintenance - pd.to_datetime('today') < months
