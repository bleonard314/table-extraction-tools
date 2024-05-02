from shiny import App, ui, reactive, render, req#, download
import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import plotly.graph_objects as go

# Load environment variables
load_dotenv()

# Establish database connection
engine = create_engine(os.getenv("DB_CONNECTION"))

# Reactive expression for retrieving and preprocessing data
@reactive.Calc
def get_data():
    query = f"SELECT * FROM {os.getenv('DB_TABLE')} ORDER BY table_order, result_order"
    df = pd.read_sql(query, engine)
    df['date_sampled'] = pd.to_datetime(df['date_sampled']).dt.strftime('%m/%d/%Y')
    return df

# UI definition
app_ui = ui.page_fluid(
    ui.input_select("dataset", "Dataset:", choices=[]),
    ui.input_select("location_id", "Location ID:", choices=[]),
    ui.input_select("analyte_group", "Analyte Group:", choices=[]),
    ui.input_select("analyte", "Analyte:", choices=[]),
    ui.output_plot("plot"),
    ui.input_action_button("download", "Download Excel")
)

# Server logic
def server(input, output, session):
    @reactive.Effect
    @reactive.event(input.dataset)
    def _():
        df = get_data()
        datasets = df['title'].unique()
        ui.update_select(input_id="dataset", choices=datasets, selected=datasets[0] if len(datasets) > 0 else None)

    @reactive.Calc
    def filtered_data():
        df = get_data()
        return df[(df['title'] == req(input.dataset)) & 
                  (df['location_id'] == req(input.location_id)) & 
                  (df['analyte_group'] == req(input.analyte_group)) & 
                  (df['analyte'] == req(input.analyte))]

    @output
    @render.plot
    def plot():
        df_filtered = filtered_data()
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=df_filtered['client_id'],
                                   y=df_filtered['conc_rl'],
                                   mode='markers',
                                   marker=dict(color='LightSkyBlue'),
                                   text=df_filtered['lab_id'],
                                   name='Concentration'))
        fig.update_layout(title='Sample Concentration per Client ID',
                          xaxis_title='Client ID',
                          yaxis_title='Concentration',
                          legend_title='Legend')
        return fig

    # Download functionality
    # @download.handler("download")
    # def download_data():
    #     df_filtered = filtered_data()
    #     filename = "/tmp/filtered_data.xlsx"
    #     df_filtered.to_excel(filename, index=False)
    #     return filename

app = App(app_ui, server)
