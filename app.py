# ETF 별 종가 추이를 호출하는 함수

from pykrx import stock
import requests
import json
from pandas.io.json import json_normalize
import pandas as pd
from datetime import datetime
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import dash_table
from dash.dependencies import Input, Output, State


url = 'https://finance.naver.com/api/sise/etfItemList.nhn'
json_data = json.loads(requests.get(url).text)

df = pd.json_normalize(json_data['result']['etfItemList'])
df = df[['itemcode','itemname']]
df = df.rename(columns = {"itemcode":"종목코드", "itemname":"종목명"})

# ESG_ TICKER를 추출합니다.
ESG_TICKER = df[df['종목명'].str.contains('ESG')][1:]

# TICKER별로 종가 데이터를 누적합니다.
stocks = dict()
for NAME,TICKER in ESG_TICKER[['종목명','종목코드']].itertuples(index=False):
    price = stock.get_etf_ohlcv_by_date('20191201', '20210523', TICKER)
    stocks[NAME] = price['종가'].values[:].tolist()
df_price = pd.DataFrame(stocks)
df_price.index = price.index

# 데이터 Layout을 변환합니다.
df_price = df_price.reset_index().rename(columns={"index": "id"})
df_price['날짜'] = df_price['날짜'].astype('str')
df_price['날짜'] = df_price['날짜'].apply(lambda _ : datetime.strptime(_,'%Y-%m-%d'))
df_fig = pd.melt(df_price,id_vars=['날짜'], var_name = '종목코드', value_name = '종가')

df_fig = px.line(df_fig, x='날짜', y='종가', color = '종목코드')



external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.H3("ESG ETF 종가 추이 "),
    dcc.Graph(
        id = 'my-graph',
        style={'height': 600},
        figure = df_fig
    ),
    dash_table.DataTable(
        id="datatable-interactivity",
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
        page_size=15,  # number of rows visible per page
        style_cell={  # ensure adequate header width when text is shorter than cell's text
            "minWidth": 150,
            "maxWidth": 250,
            "width": 200,
        },
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
        }
    )
])



if __name__ == "__main__":
    app.run_server(debug=True, port=8060)



