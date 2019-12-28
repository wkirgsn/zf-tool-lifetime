
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import dash_daq as daq


class LayoutBuilder:
    """Class for building the dashboard layout."""

    about = ("""
###### What is this mock app about?

This is a dashboard for monitoring real-time process quality along manufacture production line. 

###### What does this app shows

Click on buttons in `Parameter` column to visualize details of measurement trendlines on the bottom panel.

The sparkline on top panel and control chart on bottom panel show Shewhart process monitor using mock data. 
The trend is updated every other second to simulate real-time measurements. Data falling outside of six-sigma control limit are signals indicating 'Out of Control(OOC)', and will 
trigger alerts instantly for a detailed checkup. 

Operators may stop measurement by clicking on `Stop` button, and edit specification parameters by clicking specification tab.

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
        color_green = "#7ee37b"
        color_yellow = "#f4d44d"
        color_red = "#FF0000"
        attrition_thresh_1 = 0.6
        attrition_thresh_2 = 0.85
        column_attributes = [dict(className='one column',
                                  style={"margin-right": "2.5rem",
                                         "minWidth": "50px",
                                         'textAlign': 'center'},
                                  children=html.Div("Form")),
                             dict(className='four column',
                                  style={"height": "100%",
                                         "margin-top": "5rem"
                                         },
                                  children=html.Div("Haltbarkeit")),
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
                             ]

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

            div_attrs = self.column_attributes.copy()

            for default_attr, specific_attr in zip(div_attrs, cols):
                default_attr.update(specific_attr)
            return html.Div(id=div_id,
                            className="row metric-row",
                            style=style,
                            children=[html.Div(**c) for c in div_attrs])

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

            div_attrs = [div_id, None,
                {"id": item, "children": item},  # form nr
                {"id": gradbar_id + "_container",  # Haltbarkeit
                 "children": daq.GraduatedBar(
                    id=gradbar_id,
                    showCurrentValue=False, max=20, size=140,
                    color={
                         "ranges": {
                             "#92e0d3": [0, 20*self.attrition_thresh_1],
                             "#f4d44d ": [20*self.attrition_thresh_1,
                                          20*self.attrition_thresh_2],
                             "#f45060": [20*self.attrition_thresh_2, 20],
                         }
                     },
                    value=20*self.dm.relative_attritions_per_form[item])
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
                         id=is_crit_id, value=True, color="#91dfd2",
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

                def callback(interval, stored_data):
                    spark_line = go.Figure(
                        self._get_sparkline_config(_form))
                    attrition = attritions[_form]

                    if self.dm.maintenance_of_form_within_months(3):
                        is_crit_color = self.color_red
                    elif self.dm.maintenance_of_form_within_months(6):
                        is_crit_color = self.color_yellow
                    else:
                        is_crit_color = self.color_green
                    next_maintenance = self.dm.next_maintenance(_form)
                    return 20*attrition, \
                           spark_line,\
                           is_crit_color, \
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
                    inputs=[Input("interval-component", "n_intervals")],
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
                            label="Upload Data",
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
                        dcc.Tab(
                            id="ml-tab",
                            label="Machine Learning",
                            value="tab3",
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
    def generate_piechart():
        return dcc.Graph(
            id="piechart",
            figure={
                "data": [
                    {
                        "labels": [],
                        "values": [],
                        "type": "pie",
                        "marker": {"line": {"color": "white", "width": 1}},
                        "hoverinfo": "label",
                        "textinfo": "label",
                    }
                ],
                "layout": {
                    "margin": dict(l=20, r=20, t=20, b=20),
                    "showlegend": True,
                    "paper_bgcolor": "rgba(0,0,0,0)",
                    "plot_bgcolor": "rgba(0,0,0,0)",
                    "font": {"color": "white"},
                    "autosize": True,
                },
            },
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

    def build_quick_stats_panel(self):
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
                        html.P("Durchschnittl. Formhaltbarkeit"),
                        daq.GraduatedBar(
                            id="form-life-bar",
                            value=self.dm.avg_attrition
                        ),
                    ],
                ),
                html.Div(
                    id="card-3",
                    children=[
                        html.P("Gießzellenauslastung"),
                        daq.Gauge(id="attrition-gauge",
                                    min=0, max=100, showCurrentValue=True)],
                ),
                html.Div(
                    id="card-4",
                    children=[
                        html.P("AI"),
                        daq.PowerButton(id="AI-powerbutton", on=False)],
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
        forms = self.dm.bedarf_formen.Form.unique().tolist()
        # todo: rewrite below
        return [
            # Manually select metrics
            html.Div(
                id="set-specs-intro-container",
                # className='twelve columns',
                children=html.P(
                    "Edit specifications for forms and products or "
                    "customer orders"
                ),
            ),
            html.Div(
                id="settings-menu",
                children=[
                    html.Div(
                        id="metric-select-menu",
                        # className='five columns',
                        children=[
                            html.Label(id="metric-select-title",
                                       children="Select Metrics"),
                            html.Br(),
                            dcc.Dropdown(
                                id="metric-select-dropdown",
                                options=list(
                                    {"label": param, "value": param} for param in
                                    forms
                                ),
                                value=forms[1],
                            ),
                        ],
                    ),
                    html.Div(
                        id="value-setter-menu",
                        # className='six columns',
                        children=[
                            html.Div(id="value-setter-panel"),
                            html.Br(),
                            html.Div(
                                id="button-div",
                                children=[
                                    html.Button("Update", id="value-setter-set-btn"),
                                    html.Button(
                                        "View current setup",
                                        id="value-setter-view-btn",
                                        n_clicks=0,
                                    ),
                                ],
                            ),
                            html.Div(
                                id="value-setter-view-output", className="output-datatable"
                            ),
                        ],
                    ),
                ],
            ),
        ]

    def build_monitoring_tab(self):
        return html.Div(
                id="status-container",
                children=[
                    self.build_quick_stats_panel(),
                    html.Div(
                        id="graphs-container",
                        children=[self.build_forms_panel(),
                                  self.build_orders_panel(),
                                  # todo: lb.build_giesszellenbedarf_panel()
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
                        # generate_piechart(),
                        self.build_next_maintenance_dates()
                    ],
                ),
            ],
        )

    def build_next_maintenance_dates(self):
        return html.Div(id='next_maintenances',
                        children=[html.Div(children=m) for m in
                                  self.dm.maintenances_in_next_months()])

    def build_orders_panel(self):
        return html.Div(
            id="middle-section-container",
            className="twelve columns",
            children=[
                self.build_section_banner("Bestellübersicht"),
                dcc.Graph(
                    id="order-overview",
                    figure=go.Figure(
                        {
                            "data": [
                                {
                                    "x": [],
                                    "y": [],
                                    "mode": "lines+markers",
                                    "name": 'what name?',
                                }
                            ],
                            "layout": {
                                "paper_bgcolor": "rgba(0,0,0,0)",
                                "plot_bgcolor": "rgba(0,0,0,0)",
                                "xaxis": dict(
                                    showline=False, showgrid=False,
                                    zeroline=False
                                ),
                                "yaxis": dict(
                                    showgrid=False, showline=False,
                                    zeroline=False
                                ),
                                "autosize": True,
                            },
                        }
                    ),
                ),
            ],
        )

    def generate_order_chart(self, interval, specs_dict, col):

        ser = self.dm.orders_df.groupby('date').sum().loc[self.dm.today:,
                'amt_orders']

        """ooc_trace = {
            "x": [],
            "y": [],
            "name": "Out of Control",
            "mode": "markers",
            "marker": dict(color="rgba(210, 77, 87, 0.7)", symbol="square",
                           size=11),
        }

        for index, data in enumerate(y_array[:total_count]):
            if data >= ucl or data <= lcl:
                ooc_trace["x"].append(index + 1)
                ooc_trace["y"].append(data)"""

        histo_trace = {
            "x": ser.index,
            "y": ser,
            "type": "histogram",
            "orientation": "h",
            "name": "Distribution",
            "xaxis": "x2",
            "yaxis": "y2",
            "marker": {"color": "#f4d44d"},
        }

        fig = {"data": [
                    {
                        "x": ser.index,
                        "y": ser,
                        "mode": "lines+markers",
                        "name": col,
                        "line": {"color": "#f4d44d"},
                    },
                    # ooc_trace,
                    histo_trace,
                    ],
                "layout": dict(
                    margin=dict(t=40),
                    hovermode="closest",
                    uirevision=col,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend={"font": {"color": "darkgray"}, "orientation": "h", "x": 0,
                            "y": 1.1},
                    font={"color": "darkgray"},
                    showlegend=True,
                    xaxis={
                        "zeroline": False,
                        "showgrid": False,
                        "title": "Batch Number",
                        "showline": False,
                        "domain": [0, 0.8],
                        "titlefont": {"color": "darkgray"},
                    },
                    yaxis={
                        "title": col,
                        "showgrid": False,
                        "showline": False,
                        "zeroline": False,
                        "autorange": True,
                        "titlefont": {"color": "darkgray"},
                    },

                    xaxis2={
                        "title": "Count",
                        "domain": [0.8, 1],  # 70 to 100 % of width
                        "titlefont": {"color": "darkgray"},
                        "showgrid": False,
                    },
                    yaxis2={
                        "anchor": "free",
                        "overlaying": "y",
                        "side": "right",
                        "showticklabels": False,
                        "titlefont": {"color": "darkgray"},
                },
        )}

        return fig

