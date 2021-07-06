# ETF 별 누적수익률 추이를 호출하는 함수

from pykrx import stock
import FinanceDataReader as fdr
import pandas as pd
import requests
import json
from pandas.io.json import json_normalize
import pandas as pd
from datetime import datetime, date
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc


# ESG ETF 리스트
df_etf_kr = fdr.EtfListing('KR')
df_esg_etf_list = df_etf_kr[df_etf_kr['Name'].str.contains('ESG')] # ETF > ESG 리스트
df_kospi_kr = fdr.StockListing('KOSPI') # KOSPI리스트
df_kosdaq_kr = fdr.StockListing('KOSDAQ') # KOSPI리스트
df_ks_kr = pd.concat([df_kospi_kr, df_kosdaq_kr], ignore_index = True)
df_stock_list = df_ks_kr.dropna(subset=['Sector']) # KR > 종목리스트


std_date = '20210101'
TICKER = '289040' # KODEX MSCI KOREA ESG유니버설

def get_ETF_PDF(TICKER, std_date):
    df = stock.get_etf_portfolio_deposit_file(TICKER, std_date)
    df = df.reset_index(drop=False)
    df = df.rename(columns={'티커':'Symbol'})
    df = pd.merge(df,df_stock_list)
    df['기준가'] = round(df['금액'] /df['계약수'])
    df = df[['Symbol','Name','Market','Sector','기준가','계약수','금액','비중']]
    df = df.rename(columns={'Symbol':'TICKER','Name':'종목명'})
    df = df.reset_index(drop=True)
    ETF_PDF = df
    return ETF_PDF

ETF_PDF = get_ETF_PDF('289040','20210628')

def get_ETF_return(start_date, end_date, TICKER):
    df = stock.get_etf_ohlcv_by_date(start_date, end_date, TICKER)
    df = df.reset_index(drop=False)
    df['Symbol'] = TICKER
    df = pd.merge(df,df_esg_etf_list, how = "inner", on = "Symbol")
    df = df[['날짜','Symbol','Name','종가','NAV','거래량','기초지수']]
    df = df.rename(columns={'Symbol':'TICKER','Name':'ETF명'})
    df['수익률'] = (df['종가'] / df['종가'].shift(1)) - 1
    df['누적수익률'] = (1 + df['수익률']).cumprod() - 1
    ETF_return = df.dropna(axis=0)
    return ETF_return


def get_ESG_data(start_date,end_date):
    url = 'https://finance.naver.com/api/sise/etfItemList.nhn'
    json_data = json.loads(requests.get(url).text)

    df = pd.json_normalize(json_data['result']['etfItemList'])
    df = df[['itemcode','itemname']]
    df = df.rename(columns = {"itemcode":"종목코드", "itemname":"종목명"})

    # ESG_ TICKER를 추출합니다.
    ESG_TICKER = df[df['종목명'].str.contains('ESG')][1:]
    mask = ESG_TICKER['종목코드'].isin(['385590'])
    ESG_TICKER = ESG_TICKER[~mask]


    # TICKER별로 종가 데이터를 누적합니다.
    stock_price = dict()
    stock_rtn_cum = dict()
    for NAME,TICKER in ESG_TICKER[['종목명','종목코드']].itertuples(index=False):
        df = stock.get_etf_ohlcv_by_date(start_date, end_date, TICKER)
        df['수익률'] = (df['종가'] / df['종가'].shift(1)) - 1
        df['누적수익률'] = (1 + df['수익률']).cumprod() - 1
        stock_price[NAME] = df['종가'].values[:].tolist()
        stock_rtn_cum[NAME] = df['누적수익률'].values[:].tolist()
    df_price = pd.DataFrame(stock_price)
    df_rtn_cum = pd.DataFrame(stock_rtn_cum)
    df_price.index = df.index
    df_rtn_cum.index = df.index

    # 데이터 Layout을 변환합니다.
    df_price = df_price.reset_index().rename(columns={"index": "id"})
    df_rtn_cum = df_rtn_cum.reset_index().rename(columns={"index": "id"})
    return df_rtn_cum, df_price

# Default  값
df_rtn_cum = get_ESG_data('20200101', '20210628')[0]
df_price = get_ESG_data('20200101', '20210628')[1]
df_rtn_cum = df_rtn_cum.dropna()
df_price = df_price.dropna()
df_fig = pd.melt(df_rtn_cum,id_vars=['날짜'], var_name = '종목코드', value_name = '누적수익률')
df_fig = px.line(df_fig, x='날짜', y='누적수익률', color = '종목코드')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# styling the sidebar
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

# padding for the page content
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [
        html.H2("ESG Dash", className="display-4"),
        html.Hr(),
        html.P(
            "ETF & Index", className="lead"
        ),
        dbc.Nav(
            [
                dbc.NavLink("ESG ETF", href="/", active="exact"),
                dbc.NavLink("ESF Index", href="/page-1", active="exact")
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content", children=[], style=CONTENT_STYLE)

app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    content
])

@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def render_page_content(pathname):
    if pathname == "/":
        return html.Div([
    dcc.Tabs([
        dcc.Tab(label = "ESG_PDF", children = [
            html.Hr(),
            html.H3("ESG별 PDF 정보"),
            html.Hr(),
            html.H5(" * 날짜 입력"),
            dcc.DatePickerSingle(
                id="my-date-picker-single",
                min_date_allowed=date(2015, 1, 1),
                initial_visible_month=date(2021, 6, 28),
                display_format='YYYYMMDD'
                ),
            html.Hr(),
            html.H5(" * PDF TICKER"),
            dcc.Dropdown(id='dropdown-TICKER', options=[], multi=True),
            dash_table.DataTable(
                id="datatable-interactivity",
                columns=[
                    {
                        "name": i,
                        "id": i,
                        "deletable": True,
                        "selectable": True,
                        "hideable": False,
                    }
                    for i in ETF_PDF.columns
                ],
                data=ETF_PDF.to_dict("records"),  # the contents of the table
                sort_action="native",  # enables data to be sorted per-column by user or not ('none')
                sort_mode="single",  # sort across 'multi' or 'single' columns
                page_action="native",  # all data is passed to the table up-front or not ('none')
                page_size=30,  # number of rows visible per page
                style_cell={  # ensure adequate header width when text is shorter than cell's text
                    "minWidth": 95,
                    "maxWidth": 200,
                    "width": 95,
                },
                # style_cell_conditional={
                #     'textAlign': 'left'
                # },
                style_data={  # overflow cells' content into multiple lines
                    "whiteSpace": "normal",
                    "height": "auto",
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                })
            ]),
            dcc.Tab(label="누적수익률", children=[
                html.H3("ESG 누적 수익률"),
                html.Hr(),
                html.H5(" * 날짜 입력"),
                dcc.DatePickerRange(
                        id="my-date-picker-range",
                        min_date_allowed=date(2015, 1, 1),
                        start_date_placeholder_text='20200505',
                        end_date_placeholder_text='20210628',
                        display_format='YYYYMMDD'
                    ),
                dcc.Graph(
                    id = 'my-graph',
                    style={'height': 600},
                    figure = df_fig
                ),
                html.Hr(),
                html.H5(" * ETF별 종가 추이"),
                dash_table.DataTable(
                    id="datatable-interactivity_secu",
                    columns=[
                        {
                            "name": i,
                            "id": i,
                            "deletable": False,
                            "selectable": True,
                            "hideable": False,
                        }
                        for i in df_price.columns
                    ],
                    data=df_price.to_dict("records"),  # the contents of the table
                    sort_action="native",  # enables data to be sorted per-column by user or not ('none')
                    sort_mode="single",  # sort across 'multi' or 'single' columns
                    page_action="native",  # all data is passed to the table up-front or not ('none')
                    page_size=20,  # number of rows visible per page
                    style_cell={  # ensure adequate header width when text is shorter than cell's text
                        "minWidth": 95,
                        "maxWidth": 200,
                        "width": 95,
                    },
                    # style_cell_conditional={
                    #     'textAlign': 'left'
                    # },
                    style_data={  # overflow cells' content into multiple lines
                        "whiteSpace": "normal",
                        "height": "auto",
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    })
                ])
        ])
        ])
    elif pathname == "/page-1":
        return [
            html.H1('good',
                    style={'textAlign': 'center'}),
            dcc.Graph(id='bargraph',
                      figure=px.bar(df, barmode='group', x='Years',
                                    y=['Girls Grade School', 'Boys Grade School']))
        ]
    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


@app.callback(
    Output('my-graph', 'figure'),
    [Input('my-date-picker-range', 'start_date'),
     Input('my-date-picker-range', 'end_date')])
def update_graph(start_date, end_date):
    def get_ESG_data(start_date, end_date):
        url = 'https://finance.naver.com/api/sise/etfItemList.nhn'
        json_data = json.loads(requests.get(url).text)

        df = pd.json_normalize(json_data['result']['etfItemList'])
        df = df[['itemcode', 'itemname']]
        df = df.rename(columns={"itemcode": "종목코드", "itemname": "종목명"})

        # ESG_ TICKER를 추출합니다.
        ESG_TICKER = df[df['종목명'].str.contains('ESG')][1:]
        mask = ESG_TICKER['종목코드'].isin(['385590'])
        ESG_TICKER = ESG_TICKER[~mask]

        # TICKER별로 종가 데이터를 누적합니다.
        stock_price = dict()
        stock_rtn_cum = dict()
        for NAME, TICKER in ESG_TICKER[['종목명', '종목코드']].itertuples(index=False):
            df = stock.get_etf_ohlcv_by_date(start_date, end_date, TICKER)
            df['수익률'] = (df['종가'] / df['종가'].shift(1)) - 1
            df['누적수익률'] = (1 + df['수익률']).cumprod() - 1
            stock_price[NAME] = df['종가'].values[:].tolist()
            stock_rtn_cum[NAME] = df['누적수익률'].values[:].tolist()
        df_price = pd.DataFrame(stock_price)
        df_rtn_cum = pd.DataFrame(stock_rtn_cum)
        df_price.index = df.index
        df_rtn_cum.index = df.index

        # 데이터 Layout을 변환합니다.
        df_price = df_price.reset_index().rename(columns={"index": "id"})
        df_rtn_cum = df_rtn_cum.reset_index().rename(columns={"index": "id"})
        return df_rtn_cum, df_price

    # Default  값
    df_rtn_cum = get_ESG_data(start_date, end_date)[0]
    df_rtn_cum = df_rtn_cum.dropna()
    df_fig = pd.melt(df_rtn_cum, id_vars=['날짜'], var_name='종목코드', value_name='누적수익률')
    df_fig = px.line(df_fig, x='날짜', y='누적수익률', color='종목코드')
    return df_fig


if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
