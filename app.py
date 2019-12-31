import pandas as pd

import dash
import dash_html_components as html
from dash.dependencies import Input, Output, State

from utils.data_gen import DataManager
from utils.layout import LayoutBuilder


app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport",
                "content": "width=device-width, initial-scale=1"}],
)
server = app.server
app.config["suppress_callback_exceptions"] = True

dm = DataManager()
lb = LayoutBuilder(app, dm)

# main structure
app.layout = lb.build_main_structure()


@app.callback(
    Output("app-content", "children"),
    [Input("app-tabs", "value")])
def render_tab_content(tab_switch):
    tab_funcs = {'tab1': lb.build_upload_data_tab,
                 'tab2': lb.build_monitoring_tab,
                 'tab3': lb.build_ml_tab}
    chosen_tab_func = tab_funcs.get(tab_switch, None)
    if chosen_tab_func is None:
        raise ValueError()
    else:
        return chosen_tab_func()


# ======= Callbacks for ABOUT popup =======
@app.callback(
    Output("markdown", "style"),
    [Input("about-button", "n_clicks"),
     Input("markdown_close", "n_clicks")],
)
def update_click_output(button_click, close_click):
    ctx = dash.callback_context
    if ctx.triggered:
        prop_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if prop_id == "about-button":
            return {"display": "block"}
    return {"display": "none"}


# ======= Callbacks for Data Upload Tab =======

@app.callback(
    Output("orders-table-content", 'children'),
    [Input("value-setter-set-btn", 'n_clicks'),
     Input("metric-select-dropdown-customer", 'value'),
     Input("metric-select-dropdown-product", 'value'),
     Input("date-picker-single", 'date'),
     Input('drag-n-drop', 'contents')],
    [State('abrufmenge-input', 'value'),
     State('drag-n-drop', 'filename'),
     State('drag-n-drop', 'last_modified')]
)
def update_orders(n_clicks, customers, products, date, dragged_content, amt,
                  dragged_filename, dragged_last_mod):
    """Callback function for the display of current dataset."""

    def a_selection_is_given(selection):
        is_given = False
        if selection is not None:
            if not isinstance(selection, list):
                selection = [selection]
            if len(selection) > 0:
                is_given = True
        return is_given

    date = pd.to_datetime(date).strftime(dm.time_format)
    ctx = dash.callback_context

    # what has triggered this callback function?
    if ctx.triggered:
        prop_id, prop_type = ctx.triggered[0]['prop_id'].split('.')
        if prop_id == 'value-setter-set-btn':
            if n_clicks > 0:
                customers_given = a_selection_is_given(customers)
                products_given = a_selection_is_given(products)
                # month is always given due to date picker component
                if customers_given and products_given:
                    dm.update_orders(customers, products, date, amt)
                else:
                    return html.Div(
                        'Please specify at least one customer and one product!')
        elif prop_id == 'drag-n-drop':
            if dragged_content is not None:
                try:
                    dm.parse_upload(dragged_content, dragged_filename,
                                    dragged_last_mod)
                except Exception as e:
                    print(e)
                    return html.Div(['There was an error processing this '
                                     'file. Please make sure to upload only '
                                     '.csv or .xls/x files. Moreover, the file '
                                     'structure has to comply with the '
                                     'following header:\n '
                                     'Kunde,Produktnummer,Jan-xx,Feb-xx,'
                                     'Mar-xx,Apr-xx,May-xx,Jun-xx,Jul-xx,'
                                     'Aug-xx,Sep-xx,Oct-xx,Nov-xx,Dec-xx,'
                                     'Gesamt'])
    return lb.generate_order_table_content(customers, products, date)


lb.generate_form_panel_callbacks()


#  ======= middle panel (orders) ============
# todo: this callback should work on textfield filters instead of app-tabs.value
@app.callback(
    output=Output("order-overview", "figure"),
    inputs=[Input("app-tabs", "value")],
    state=[State("value-setter-store", "data"),
           State("order-overview", "figure")],
)
def update_order_chart(_, data, cur_fig):
    customers = [1]  # todo: should come from some filter (textfield)
    return lb.update_order_chart(customers)


@app.callback(
    output=Output("order-piechart", "figure"),
    inputs=[Input("app-tabs", "value")],
    state=[State("value-setter-store", "data")],
)
def update_order_piechart(_, stored_data):
    customers = [1]  # todo: should come from some filter (textfield)
    return lb.update_order_pie(customers)


# Running the server
if __name__ == "__main__":
    app.run_server(debug=False, port=8050, host='0.0.0.0')
