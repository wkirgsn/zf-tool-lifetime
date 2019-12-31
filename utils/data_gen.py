import base64
import io
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
        #  pre-declare to comfy with PEP
        self.prod_form_map, self.prod_giesszellenbedarf_map, \
        self.form_attritions_over_time, self.cache = None, None, None, None

        self.calculate_additional_features()

    @property
    def unique_forms(self):
        return self.bedarf_formen.Form.unique().tolist()

    @property
    def unique_products(self):
        return self.prod_form_map.index.tolist()

    @property
    def unique_customers(self):
        return self.orders_df.Kunde.unique().tolist()

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

    @property
    def camera_ready_orders(self):
        return self.orders_df\
                        .reset_index(drop=True).loc[:, ['Kunde',
                                                        'Produktnummer',
                                                        'date',
                                                        'amt_orders']]\
                        .rename(columns=dict(amt_orders='Bestellmenge',
                                             Produktnummer='Produkt'))

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

    def delete_cache(self):
        self.cache = {}

    def calculate_additional_features(self):
        """Additional dataframes will be calculated on the base of orders_df,
         unique_forms and forms_per_prod_df"""

        attrition_by_product = \
            self.orders_df.Produktnummer.map(
                self.forms_per_prod_df[['Produktnummer', 'Bedarf']]
                    .groupby('Produktnummer').sum().Bedarf.to_dict())
        self.orders_df['total_attrition'] = \
            self.orders_df.amt_orders * attrition_by_product

        unique_forms = self.unique_forms
        self.prod_form_map = \
            self.forms_per_prod_df.pivot(index='Produktnummer', columns='Form',
                                         values='Bedarf')[unique_forms]
        self.prod_giesszellenbedarf_map = self.prod_form_map * \
                                          self.bedarf_formen['Gießzellenbedarf'] \
                                              .values.T
        # prod_form_map.loc[56, 'F6']
        orders_x_forms_df = self.orders_df.merge(
            self.prod_form_map.reset_index(),
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
        maintenance = (next_attritions - duration_left.values[np.newaxis,
                                         :]) < 0
        next_maintenance = maintenance.sum()
        self.bedarf_formen['next maintenance'] = next_attritions.index[
            next_maintenance.clip(upper=
                                  len(maintenance) - 1)]
        self.cache = {}

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
        return ((next_maintenance -
                 pd.to_datetime('today'))/np.timedelta64(1, 'M')) < months

    def form_is_critical(self, form):
        if self.maintenance_of_form_within_months(form, 3):
            color_idx = 0
        elif self.maintenance_of_form_within_months(form, 6):
            color_idx = 1
        else:
            color_idx = 2
        return color_idx

    def orders_over_time(self, customers=(1, 2)):
        """Get a nicely sorted df of orders summed over customers"""

        today = self.today
        cust_key = '_'.join(str(c) for c in customers)
        _cached_orders = self.cache.get(today, None)
        if _cached_orders is not None:
            _cached_orders_for_customers = _cached_orders.get(cust_key, None)
            if _cached_orders_for_customers is not None:
                return _cached_orders_for_customers
        else:
            self.cache[today] = {}
        # no cache available
        ret = (self.orders_df
               .loc[self.orders_df.Kunde.isin(customers), :]
               .drop(['Kunde', 'total_attrition'], axis=1)
               .groupby(['Produktnummer', 'date']).sum()  # sum over customers
               .reset_index()
               .pivot(index='date', columns='Produktnummer',
                      values='amt_orders')
               .assign(date_dt=lambda x: pd.to_datetime(x.index,
                                                        format=self.time_format))
               .sort_values(by=['date_dt']).drop('date_dt', axis=1)
               .loc[self.today:, :])
        self.cache[today][cust_key] = ret
        return ret

    def giesszellenbedarf_over_time(self, customers=(1, 2)):
        orders_over_time = self.orders_over_time(customers)
        prod_giess = self.prod_giesszellenbedarf_map.sum(axis=1)
        return prod_giess * orders_over_time

    def update_orders(self, customers, products, date, amt):
        """Update orders_df with what was specified by the user and
        submitted through the update button"""

        if date not in self.orders_df.date.tolist():
            # add new date
            self.orders_df = \
                pd.concat([self.orders_df] +
                          [pd.DataFrame(
                              {'Kunde': k,
                               'Produktnummer':
                                   self.orders_df.Produktnummer.unique().tolist(),
                               'date': date,
                               'amt_orders': 0}) for k in customers],
                          ignore_index=True, sort=False)
        mask = (self.orders_df.Kunde.isin(customers) &
                self.orders_df.Produktnummer.isin(products) &
                self.orders_df.date.isin([date]))
        assert len(self.orders_df.loc[mask, :]) > 0, 'filter error'
        self.orders_df.loc[mask, 'amt_orders'] += amt
        # avoid negative orders
        self.orders_df.amt_orders = self.orders_df.amt_orders.clip(lower=0)
        # recalculate additional features
        self.calculate_additional_features()

    def parse_upload(self, contents, filename, last_mod):
        content_type, content_string = contents.split(',')

        decoded = base64.b64decode(content_string)

        if filename.endswith('.csv'):
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif filename.endswith(('.xls', '.xlsx')):
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            raise ValueError('Wrong file extension!')
        df = df.reset_index(drop=True).dropna().astype(np.uint32)
        self.orders_df = pd.concat([self.orders_df,
                                    self._prettify_orders(df)],
                                   ignore_index=True, sort=False)
        # remove redundant entries
        #  There can be only unique customer-product-date triplets
        #  Keeping the last entry, which is the newly uploaded one
        self.orders_df = self.orders_df.drop_duplicates(subset=[
            'Produktnummer', 'date', 'Kunde'], keep='last').reset_index(
            drop=True)
