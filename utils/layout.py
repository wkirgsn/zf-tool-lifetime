import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import dash_daq as daq
from datetime import date as dt


class LayoutBuilder:
    """Class for building the dashboard layout."""

    about = ("""
###### Prozesskontrolle für Gießzellen, Gussformen und Produktbestellungen.
Entwickelt von Wilhelm Kirchgässner für IT-Talents und ZF Friedrichshafen.

Dieses Dashboard hilft den Operatoren den Überblick über den Werkzeugbestand 
zu behalten als auch der Logistik neue Bestellungen zu erfassen.


###### Datenerfassung

Füge dem Datenbestand entweder neue Einzelbestellungen, Batch-Bestellungen 
oder einen völlig neuen weiteren Datensatz hinzu.
Der aktuelle Datensatz wird automatisch gefiltert und zeigt alle Bestellungen 
der momentan ausgewählten Abrufzeiten, Kunden und Produkte.
Mit Klick auf den "Update"-Knopf werden die erfassten neuen Bestellungen dem 
aktuellen Datensatz hinzugefügt. Dabei sind Stornierungen ebenso möglich, 
indem man eine negative Zahl als Abrufmenge definiert.

Über das Drag-n-Drop Feld lässt sich eine CSV- oder XLS/X-Datei hochladen, 
welche in den aktuellen Datensatz eingebettet wird (bitte Format beachten).

Wichtig: Neue Kunden, Gußformen oder Produkte können hier nicht aufgenommen 
werden. Wenden Sie sich dafür bitte an den Systemadministratoren.

###### Control Charts Dashboard
Das Dashboard ist in zwei grobe Bereiche aufgeteilt: Quick Stats (links bzw. 
oben bei mobiler Ansicht) mit kurzen übersichtlichen Statistiken, sowie 
detailliertere Visualisierungen auf der anderen Seite.

Der Formhaltbarkeit-Überblick zeigt wie weit der Verschleiß für jede Form 
vorangeschritten ist. Die gelbe Sparkline zeigt den zu erwartenden Verschleiß 
für die nächsten 12 Monate an. EOL (End-of-life) informiert über den Monat der 
Wartung/Austausch der Form. Ist dieser in den nächsten drei Monaten, so ist 
dies als kritisch zu bewerten (roter Indikator).

Die Produkt-Bestellübersicht, sowie die Gießzellenbedarf-Übersicht zeigen auf
einen Blick wie viel von jedem Produkt bisher bestellt wurde und welchen 
Gießzellenbedarf sie verursachen, über die nächsten 12 Monate erstreckt.
Die Kuchendiagramme daneben geben einen Überblick in welchen 
Mengenverhältnissen die verschiedenen Produkte dabei stehen.

""")

    class FormsPanelArtist:
        """Class that handles the top panel giving an overview of the form
        durability"""

        suffix_row = "_row"
        suffix_button_id = "_button"
        suffix_sparkline_graph = "_sparkline_graph"
        suffix_count = "_count"
        suffix_gradbar = '_grad_bar'
        suffix_date = '_date'
        suffix_indicator = "_indicator"
        suffix_is_crit_indicator = '_is_crit_indicator'
        suffix_eol = '_EOL'
        color_range = ["#FF0000",  # red
                       "#f4d44d",  # yellow
                       "#7ee37b",  # green
                       ]
        grad_bars_max = 15
        attrition_thresh_1 = 0.6
        attrition_thresh_2 = 0.85
        column_attributes = (dict(className='one column',
                                  style={"margin-right": "2.5rem",
                                         "minWidth": "50px",
                                         'textAlign': 'center'},
                                  children=html.Div("Form")),
                             dict(className='four column',
                                  style={"height": "100%",
                                         "margin-top": "5rem"
                                         },
                                  children=html.Div("Verschleiß")),
                             dict(className='four columns',
                                  style={"height": "100%"},
                                  children=html.Div("Erwartete Abnutzung")),
                             dict(className='two column',
                                  style={},
                                  children=html.Div("EOL")),
                             dict(className='one column',
                                  style={"display": "flex",
                                         "justifyContent": "center",
                                         },
                                  children=html.Div("Kritisch")),
                             )

        def __init__(self, app, dm):
            """Needs a datamanager for row/column content, and the app
            instance for callback creation."""
            self.app = app
            self.dm = dm

            self.form_attritions_over_time = \
                self.dm.form_attritions_over_time.loc[self.dm.today:, :]\
                    .iloc[:13, :]

        def _paint_header(self):
            """Builds the form panel header."""
            # add div_ids
            div_attrs = [dict(id=f'm_header_{i}') for i
                         in range(len(self.column_attributes))]

            return self._paint_row("metric_header",
                {"height": "3rem", "margin": "1rem 0",
                 "textAlign": "center"},
                *div_attrs)

        def _paint_body(self):
            """Builds the form panel body."""
            return html.Div(id="metric-rows",
                            children=
                            [self._paint_row(*self._get_row_contents(f, i))
                                for i, f in enumerate(self.dm.unique_forms)],
                            )

        def paint(self):
            """Builds and returns the full form panel"""
            return html.Div(id="metric-div",
                            children=[self._paint_header(),
                                      self._paint_body()],
                            )

        def _paint_row(self, div_id, style, *cols):
            """Builds and returns the HTML row."""

            style = style or {"height": "8rem", "width": "100%"}

            new_div_attrs = [dict() for _ in range(len(cols))]
            div_attrs = list(self.column_attributes)

            for new_div, default_attr, specific_attr in \
                    zip(new_div_attrs, div_attrs, cols):
                new_div.update(default_attr)
                new_div.update(specific_attr)
            return html.Div(id=div_id,
                            className="row metric-row",
                            style=style,
                            children=[html.Div(**c) for c in new_div_attrs])

        def _get_row_contents(self, item, idx):
            """Build column content.

            :param item: e.g. 'F1' or 'F12'
            :param idx: Counting variable of items
            :return: list of dicts explaining the div attributes
            """
            div_id = item + self.suffix_row
            gradbar_id = f'F{idx}' + self.suffix_gradbar  # special naming
            #  cos it is explicitly handled in spc-custom-styles.css
            sparkline_graph_id = item + self.suffix_sparkline_graph
            is_crit_id = item + self.suffix_is_crit_indicator
            eol_id = item + self.suffix_eol
            max_bars = self.grad_bars_max
            div_attrs = [div_id, None,
                {"id": item, "children": item},  # form nr
                {"id": gradbar_id + "_container",  # Haltbarkeit
                 "children": daq.GraduatedBar(
                    id=gradbar_id,
                    showCurrentValue=False, max=max_bars, size=140,
                    color={
                         "ranges": {
                             "#92e0d3": [0,
                                         max_bars*self.attrition_thresh_1],
                             "#f4d44d ": [max_bars*self.attrition_thresh_1,
                                          max_bars*self.attrition_thresh_2],
                             "#f45060": [max_bars*self.attrition_thresh_2,
                                         max_bars],
                         }
                     },
                    value=max_bars *
                          self.dm.relative_attritions_per_form[item])
                },
                {"id": item + "_sparkline",  # Erwartete Abnutzung
                 "children": dcc.Graph(
                    id=sparkline_graph_id,
                    style={"width": "100%", "height": "95%"},
                    config={
                        "staticPlot": False,
                        "editable": False,
                        "displayModeBar": False,
                        },
                    figure=go.Figure(self._get_sparkline_config(item)),
                        ),
                },
                {  # form end of life
                    'id': eol_id,
                    'children': self.dm.next_maintenance(item)
                },
                {  # is form over 80% of its life in the next 3 months?
                     "id": is_crit_id + '_container',
                     "children": daq.Indicator(
                         id=is_crit_id, value=True,
                         color=self.color_range[self.dm.form_is_critical(item)],
                         size=12
                     ),
                 },
            ]
            return div_attrs

        def _get_sparkline_config(self, item):
            return {"data": [
                {
                    "x": self.form_attritions_over_time.index.values,
                    "y": self.form_attritions_over_time[item].values,
                    "mode": "lines+markers",
                    "name": item,
                    "line": {"color": "#f4d44d"},
                }
            ],
                "layout": {
                    "uirevision": True,
                    "margin": dict(l=0, r=0, t=0, b=0, pad=0),
                    "xaxis": dict(showline=False,
                                  showgrid=False,
                                  zeroline=False,
                                  showticklabels=False),
                    "yaxis": dict(showline=False,
                                  showgrid=False,
                                  zeroline=False,
                                  showticklabels=False),
                    "paper_bgcolor": "rgba(0,0,0,0)",
                    "plot_bgcolor": "rgba(0,0,0,0)",
                },
            }

        def generate_callbacks(self):
            """Infuse panel contents with life. This function makes the
            content updateable."""

            attritions = self.dm.relative_attritions_per_form

            def create_callback(_form):
                """Decorator for forms panel callbacks"""

                def callback(_, stored_data):
                    spark_line = go.Figure(
                        self._get_sparkline_config(_form))
                    attrition = attritions[_form]
                    crit_color = \
                        self.color_range[self.dm.form_is_critical(_form)]
                    next_maintenance = self.dm.next_maintenance(_form)
                    return self.grad_bars_max*attrition, \
                           spark_line,\
                           crit_color, \
                           next_maintenance

                return callback

            for idx, form in enumerate(self.dm.unique_forms):
                self.app.callback(
                    output=[
                        Output(f'F{idx}' + self.suffix_gradbar, "value"),
                        Output(form + self.suffix_sparkline_graph, "figure"),
                        Output(form + self.suffix_is_crit_indicator, "color"),
                        Output(form + self.suffix_eol, 'children')
                    ],
                    inputs=[Input("app-tabs", "value")],
                    state=[State("value-setter-store", "data")],
                )(create_callback(form))

    def __init__(self, app, dm):
        self.logo = app.get_asset_url("zf_logo.png")
        self.dm = dm
        self.form_artist = self.FormsPanelArtist(app, dm)

    @staticmethod
    def build_section_banner(title):
        return html.Div(className="section-banner", children=title)

    @staticmethod
    def build_tabs():
        return html.Div(
            id="tabs",
            className="tabs",
            children=[
                dcc.Tabs(
                    id="app-tabs",
                    value="tab2",
                    className="custom-tabs",
                    children=[
                        dcc.Tab(
                            id="Specs-tab",
                            label="Datenerfassung",
                            value="tab1",
                            className="custom-tab",
                            selected_className="custom-tab--selected",
                        ),
                        dcc.Tab(
                            id="Control-chart-tab",
                            label="Control Charts Dashboard",
                            value="tab2",
                            className="custom-tab",
                            selected_className="custom-tab--selected",
                        ),
                    ],
                )
            ],
        )

    @classmethod
    def build_about(cls):
        return html.Div(
            id="markdown",
            className="modal",
            children=(
                html.Div(
                    id="markdown-container",
                    className="markdown-container",
                    children=[
                        html.Div(
                            className="close-container",
                            children=html.Button(
                                "Close",
                                id="markdown_close",
                                n_clicks=0,
                                className="closeButton",
                            ),
                        ),
                        html.Div(
                            className="markdown-text",
                            children=dcc.Markdown(
                                children=cls.about
                            ),
                        ),
                    ],
                )
            ),
        )

    @staticmethod
    def build_value_setter_line(line_num, label, value, col3):
        return html.Div(
            id=line_num,
            children=[
                html.Label(label, className="four columns"),
                html.Label(value, className="four columns"),
                html.Div(col3, className="four columns"),
            ],
            className="row",
        )

    def build_main_structure(self):
        """The big picture."""
        return html.Div(
                id="big-app-container",
                children=[
                    self.build_banner(),
                    html.Div(
                        id="app-container",
                        children=[
                            self.build_tabs(),
                            # Main app
                            html.Div(id="app-content"),
                        ],
                    ),
                    dcc.Store(id="value-setter-store", data={}),
                    self.build_about(),
                ],
)

    def build_quick_stats_panel(self):
        current_giesszellenbedarf = \
            self.dm.giesszellenbedarf_over_time().iloc[0, :]
        return html.Div(
            id="quick-stats",
            className="row",
            children=[
                html.Div(
                    id="card-1",
                    children=[
                        html.P("Operator ID"),
                        daq.LEDDisplay(
                            id="operator-led",
                            value="042",
                            color="#92e0d3",
                            backgroundColor="#1e2130",
                            size=20,
                        ),
                    ],
                ),
                html.Div(
                    id="card-2",
                    children=[
                        html.P("Durchschnittl. Formverschleiß"),
                        daq.GraduatedBar(
                            id="form-life-bar",
                            value=self.dm.avg_attrition
                        ),
                    ],
                ),
                html.Div(
                    id="card-3",
                    children=[
                        html.P("Prozentuale Gießzellenauslastung diesen Monat"),
                        daq.Gauge(id="attrition-gauge",
                                  min=0, max=100, showCurrentValue=True,
                                  value=100 * current_giesszellenbedarf.mean() /
                                        current_giesszellenbedarf.max())],
                ),
                html.Div(
                    id="card-4",
                    children=
                        daq.BooleanSwitch(id="AI-powerbutton", on=False,
                                        label='AI', color="#92e0d3"),
                ),
            ],
        )

    def build_banner(self):
        return html.Div(
            id="banner",
            className="banner",
            children=[
                html.Div(
                    id="banner-text",
                    children=[
                        html.H5("Process Control Dashboard"),
                        html.H6("ZF Friedrichshafen AG"),
                    ],
                ),
                html.Div(
                    id="banner-logo",
                    children=[
                        html.Button(
                            id="about-button", children="ABOUT",
                            n_clicks=0
                        ),
                        html.Img(id="logo", src=self.logo)
                    ],
                ),
            ],
        )

    def generate_form_panel_callbacks(self):
        self.form_artist.generate_callbacks()

    def build_upload_data_tab(self):
        unique_customers = self.dm.unique_customers
        unique_products = self.dm.unique_products
        orders_df = self.dm.camera_ready_orders
        return [
            # Manually select metrics
            html.Div(
                id="set-specs-intro-container",
                # className='twelve columns',
                children=[
                    html.Div(id='specs-descr',
                             children=
                        html.P("Erfasse neue Bestellungen oder lade einen neuen "
                               "Datensatz hoch. Der aktuelle Datensatz wird automatisch "
                               f"gefiltert.")),
                     html.Div(id='led-2-container',
                              children=daq.LEDDisplay(
                                             id="operator-led-2",
                                             value="042", size=20,
                                             color="#92e0d3",
                                             label='Operator ID',
                                             backgroundColor="#1e2130"),
                              ),


                    ],
                className='double_container'
            ),
            html.Div(
                id="settings-menu",
                children=[
                    html.Div(
                        id="metric-select-menu",
                        # className='five columns',
                        children=[
                            html.Label(id="metric-select-title-customer",
                                       children="Kunde(n)"),
                            dcc.Dropdown(
                                id="metric-select-dropdown-customer",
                                options=list(
                                    {"label": param, "value": param} for
                                    param in unique_customers
                                ),
                                multi=True,
                            ),
                            html.Br(),
                            html.Label(id="metric-select-title-product",
                                       children="Produkt(e)"),
                            dcc.Dropdown(
                                id="metric-select-dropdown-product",
                                options=list(
                                    {"label": param, "value": param} for
                                    param in unique_products
                                ),
                                multi=True,
                            ),
                            html.Br(),
                            html.Label(id="metric-select-title-amt",
                                       children="Zusätzliche Abrufmenge "
                                                "(negativ für Storno)"),
                            daq.NumericInput(id='abrufmenge-input',
                                             className='setting-input',
                                             value=0,
                                             min=-999999,
                                             max=999999),
                            html.Br(),
                            html.Label(id="metric-select-title-date",
                                       children="Abrufzeitpunkt"),
                            dcc.DatePickerSingle(
                                id='date-picker-single',
                                date=dt.today()
                            ),
                            html.Br(),
                            html.Br(),
                            html.Div(
                                id="button-div",
                                children=
                                html.Button("Update",
                                            id="value-setter-set-btn",
                                            disabled=False),
                            ),
                            html.Br(),
                            dcc.Upload(id='drag-n-drop',
                                       children=html.Div([
                                                'Drag and Drop or ',
                                                html.A('Select Files')
                                            ]),
                                       style={
                                           'width': '100%',
                                           'height': '60px',
                                           'lineHeight': '60px',
                                           'borderWidth': '1px',
                                           'borderStyle': 'dashed',
                                           'borderRadius': '5px',
                                           'textAlign': 'center',
                                           'margin': '10px'
                                       })
                        ],
                    ),
                    html.Div(
                        id="orders-table-container",
                        # className='six columns',
                        children=[
                            html.H4(
                                style=dict(textAlign='center'),
                                children='Aktueller Datensatz'),
                            html.Table([
                                        # header

                                         html.Tr(
                                             [html.Th('Index')] +
                                             [html.Th(col) for col in
                                              orders_df.columns]),
                                         ],
                                        id="orders-table-head",
                                        className="output-datatable",),
                            html.Div(
                             html.Table(# body
                                 id='orders-table-content',
                                 children=self.generate_order_table_content(),
                                 title='Aktueller Datensatz',
                                 className="output-datatable",
                             ),
                            id="orders-table-body",
                            ),
                        ],
                    ),
                ],
            ),
        ]

    def generate_order_table_content(self,
                                     customers=None, products=None,
                                     month=None):
        orders_df = self.dm.camera_ready_orders
        if customers is not None:
            if not isinstance(customers, list):
                customers = [customers]
            if len(customers) > 0:
                orders_df = orders_df.loc[orders_df.Kunde.isin(customers), :]
        if products is not None:
            if not isinstance(products, list):
                products = [products]
            if len(products) > 0:
                orders_df = orders_df.loc[orders_df.Produkt.isin(products), :]
        if month is not None:
            orders_df = orders_df.loc[orders_df.date == month, :]

        return [html.Tr([html.Td(i) for i in tup]) for tup in
                orders_df.itertuples()]

    def build_monitoring_tab(self):
        return html.Div(
                id="status-container",
                children=[
                    self.build_quick_stats_panel(),
                    html.Div(
                        id="graphs-container",
                        children=[self.build_forms_panel(),
                                  self.build_orders_panel(),
                                  self.build_giesszellenbedarf_panel()
                                  ],
                    ),
                ],
            )

    def build_ml_tab(self):
        # todo: implement
        raise NotImplementedError()

    def build_forms_panel(self):
        """Builds the top panel giving an overview of all forms and their
        durability.

        :return: html.Div object
        """
        return html.Div(
            id="top-section-container",
            className="row",
            children=[
                # Metrics summary
                html.Div(
                    id="metric-summary-session",
                    className="nine columns",
                    children=[
                        self.build_section_banner("Formhaltbarkeit Überblick"),
                        self.form_artist.paint()
                    ],
                ),
                # Next Maintenance
                html.Div(
                    id="next-maintenance",
                    className="three columns",
                    children=[
                        self.build_section_banner("Nächste Wartungstermine"),
                        html.Div(id='next_maintenances',
                                 children=[html.Div(children=m) for m in
                                           self.dm.maintenances_in_next_months()
                                           ])
                    ],
                ),
            ],
        )

    def build_orders_panel(self):
        return html.Div(
            id="middle-section-container",
            className="row",
            children=[
                html.Div(id='order-overview-container',
                         className='eight columns',
                         children=[
                             self.build_section_banner(
                                 "Produkte Bestellübersicht"),
                             dcc.Graph(id="order-overview",
                                       figure=self.update_order_chart())
                         ]),
                html.Div(id='order-piechart-container',
                         className='four columns',
                         children=[
                             self.build_section_banner('Bestellverhältnisse '
                                                       'der Produkte'),
                             dcc.Graph(id="order-piechart",
                                       figure=self.update_order_pie())
                         ])
            ],
        )

    def build_giesszellenbedarf_panel(self):
        return html.Div(
            id="bottom-section-container",
            className="row",
            children=[
                html.Div(id='giess-overview-container',
                         className='eight columns',
                         children=[
                             self.build_section_banner(
                                 "Gießzellenbedarf Übersicht"),
                             dcc.Graph(id="giess-overview",
                                       figure=self.update_giess_chart())
                         ]),
                html.Div(id='giess-piechart-container',
                         className='four columns',
                         children=[
                             self.build_section_banner(
                                 'Gießzellenauslastungsverhältnis '
                                                       'der Produkte'),
                             dcc.Graph(id="giess-piechart",
                                       figure=self.update_giess_pie())
                         ])
            ],
        )

    def update_order_chart(self, customers=1):

        if not isinstance(customers, list):
            customers = [customers]

        orders_df = self.dm.orders_over_time(customers)

        fig = {"data": [{"x": orders_df.index,
                         "y": orders_df[prod],
                         "type": "bar",
                         "name": prod,
                         } for prod in orders_df],
               "layout": dict(
                   margin=dict(t=40),
                   hovermode="closest",
                   barmode='stack',
                   paper_bgcolor="rgba(0,0,0,0)",
                   plot_bgcolor="rgba(0,0,0,0)",
                   legend={"font": {"color": "darkgray"},
                           "orientation": "h", "x": 0, "y": 1.1},
                   font={"color": "darkgray"},
                   showlegend=True,
                   xaxis={
                       "zeroline": False,
                       "showgrid": False,
                       "title": "Monat und Jahr",
                       "showline": False,
                       "titlefont": {"color": "darkgray"},
                   },
                   yaxis={
                       "title": 'Gesamtbestellmenge',
                       "showgrid": False,
                       "showline": False,
                       "zeroline": False,
                       "autorange": True,
                       "titlefont": {"color": "darkgray"},
                   },

        )}

        return fig

    def update_order_pie(self, customers=1):
        if not isinstance(customers, list):
            customers = [customers]
        orders_df = self.dm.orders_over_time(customers)
        values = orders_df.values.sum(axis=0)
        values = values / values.max()  # normalize
        colors = ["#f45060" if v > 0.1 else "#91dfd2" for v in values]
        fig = {
            "data": [
                {
                    "labels": orders_df.columns.tolist(),
                    "values": values,
                    "type": "pie",
                    "marker": {"colors": colors,
                               "line": dict(color="white", width=2)},
                    "hoverinfo": "label",
                    "textinfo": "label",
                }
            ],
            "layout": {
                "margin": dict(t=20, b=50),
                "uirevision": True,
                "font": {"color": "white"},
                "showlegend": False,
                "paper_bgcolor": "rgba(0,0,0,0)",
                "plot_bgcolor": "rgba(0,0,0,0)",
                "autosize": True,
            },
        }
        return fig

    def update_giess_chart(self, customers=1):
        if not isinstance(customers, list):
            customers = [customers]
        giess_over_time = self.dm.giesszellenbedarf_over_time(customers)
        return {"data": [{"x": giess_over_time.index,
                         "y": giess_over_time[prod],
                         "type": "bar",
                         "name": prod,
                         } for prod in giess_over_time],
               "layout": dict(
                   margin=dict(t=40),
                   hovermode="closest",
                   barmode='stack',
                   paper_bgcolor="rgba(0,0,0,0)",
                   plot_bgcolor="rgba(0,0,0,0)",
                   legend={"font": {"color": "darkgray"},
                           "orientation": "h", "x": 0, "y": 1.1},
                   font={"color": "darkgray"},
                   showlegend=True,
                   xaxis={
                       "zeroline": False,
                       "showgrid": False,
                       "title": "Monat und Jahr",
                       "showline": False,
                       "titlefont": {"color": "darkgray"},
                   },
                   yaxis={
                       "title": 'Gesamtgießzellenbedarf',
                       "showgrid": False,
                       "showline": False,
                       "zeroline": False,
                       "autorange": True,
                       "titlefont": {"color": "darkgray"},
                   },

        )}

    def update_giess_pie(self, customers=1):
        if not isinstance(customers, list):
            customers = [customers]
        giess_over_time = self.dm.giesszellenbedarf_over_time(customers)
        values = giess_over_time.values.sum(axis=0)
        values = values / values.max()  # normalize
        colors = ["#f45060" if v > 0.1 else "#91dfd2" for v in values]
        fig = {
            "data": [
                {
                    "labels": giess_over_time.columns.tolist(),
                    "values": values,
                    "type": "pie",
                    "marker": {"colors": colors,
                               "line": dict(color="white", width=2)},
                    "hoverinfo": "label",
                    "textinfo": "label",
                }
            ],
            "layout": {
                "margin": dict(t=20, b=50),
                "uirevision": True,
                "font": {"color": "white"},
                "showlegend": False,
                "paper_bgcolor": "rgba(0,0,0,0)",
                "plot_bgcolor": "rgba(0,0,0,0)",
                "autosize": True,
            },
        }
        return fig