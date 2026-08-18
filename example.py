import customtkinter as ctk
import tkinter as tk
from tkintermapview import TkinterMapView
from tkintermapview.utility_functions import osm_to_decimal
from tktooltip import ToolTip
from ctk_xyframe import CTkXYFrame
import random
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTk,
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)
from frames import ScrollableRadioFrame, ScrollableCheckboxFrame, PlotFrame, FieldPlotView, IntegratedMapView
from db import Owner, Plot, Management, Image, Location, Variable, Session, engine, sessionmaker, select
# NOTICE FOR ANYONE DOWNLOADING THIS!!!
# In the tkintermapview package, find the TkinterMapView class and its set_address function
# Its first line,  result = geocoder.osm(address_string)
# MUST instead be, result = geocoder.arcgis(address_string)
# ALSO!!!
# Find ctk_xyframe.py on https://github.com/Akascape/CTkXYFrame
ctk.set_default_color_theme("blue")
MAX_RADIO_DISPLAY = 5
        

class App(ctk.CTk):

    APP_NAME = "TkinterMapView with CustomTkinter"
    WIDTH = 800
    HEIGHT = 500

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stuff = contact_server()
        self.title(App.APP_NAME)
        self.geometry(str(App.WIDTH) + "x" + str(App.HEIGHT))
        self.minsize(App.WIDTH, App.HEIGHT)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Command-q>", self.on_closing)
        self.bind("<Command-w>", self.on_closing)
        self.createcommand('tk::mac::Quit', self.on_closing)

        self.marker_list = []
        self.conn = sessionmaker(bind = engine)()

        # ============ create two CTkFrames ============

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame_left = ctk.CTkFrame(master=self, width=150, corner_radius=0, fg_color=None)
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

        self.frame_right = ctk.CTkFrame(master=self, corner_radius=0)
        self.frame_right.grid(row=0, column=1, rowspan=1, pady=0, padx=0, sticky="nsew")

        # ============ frame_left ============
        self.frame_left.grid_rowconfigure(5, weight=1)
        self.var_frame = ScrollableCheckboxFrame(self.frame_left, "Variables", command = self.draw_graph)
        self.var_frame.grid(row=0, column=0, padx=(20, 20), pady=(10, 0))
        self.radio_frame = ScrollableRadioFrame(self.frame_left, "Locations", command = self.display_field_plots)
        self.radio_frame.grid(row=0, column=0, padx=(20, 20), pady=(10, 0))
        self.map_label = ctk.CTkLabel(self.frame_left, text="Plots:", anchor="w")
        self.map_label.grid(row=4, column=0, padx=(20, 20), pady=(20, 0))
        self.plot_grid = FieldPlotView(master = self.frame_left, command = self.display_graph)
        self.plot_grid.grid(row=5, column=0, padx=(20, 20), pady=(10, 0))
        self.map_label = ctk.CTkLabel(self.frame_left, text="Tile Server:", anchor="w")
        self.map_label.grid(row=6, column=0, padx=(20, 20), pady=(20, 0))
        self.map_option_menu = ctk.CTkOptionMenu(self.frame_left, values=["OpenStreetMap", "Google Satellite"],
                                                                       command=self.change_map)
        self.map_option_menu.grid(row=7, column=0, padx=(20, 20), pady=(10, 0))

        # ============ frame_right ============

        self.frame_right.grid_rowconfigure(1, weight=1)
        self.frame_right.grid_rowconfigure(0, weight=0)
        self.frame_right.grid_columnconfigure(0, weight=1)
        self.frame_right.grid_columnconfigure(1, weight=0)
        self.frame_right.grid_columnconfigure(2, weight=1)

        self.make_figure_frame()
        self.map_widget = IntegratedMapView(self.frame_right, corner_radius=0)
        self.map_widget.grid(row=1, rowspan=1, column=0, columnspan=3, sticky="nswe", padx=(0, 0), pady=(0, 0))

        self.entry = ctk.CTkEntry(master=self.frame_right,
                                            placeholder_text="type address")
        self.entry.grid(row=0, column=0, sticky="we", padx=(12, 0), pady=12)
        self.entry.bind("<Return>", self.search_event)

        self.button_5 = ctk.CTkButton(master=self.frame_right,
                                                text="Search",
                                                width=90,
                                                command=self.search_event)
        self.button_5.grid(row=0, column=1, sticky="w", padx=(12, 0), pady=12)

        # Set default values
        self.map_widget.set_address("Arlington")
        self.map_option_menu.set("OpenStreetMap")
    
    def make_figure_frame(self):
        figure = Figure()
        # create FigureCanvasTkAgg object
        self.figure_frame = ctk.CTkFrame(self.frame_right)
        self.figure_canvas = FigureCanvasTkAgg(figure, self.figure_frame)
        self.figure_canvas.get_tk_widget().pack()
        self.ax = self.figure_canvas.figure.add_subplot(111)
        # create the toolbar
        NavigationToolbar2Tk(self.figure_canvas, self.figure_frame)
        self.figure_frame.grid(row=1, rowspan=1, column=0, columnspan=3, sticky="nswe", padx=(0, 0), pady=(0, 0))

    def search_event(self, event=None):
        self.map_widget.set_address(self.entry.get())

    def change_map(self, new_map: str):
        if new_map == "OpenStreetMap":
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        elif new_map == "Google Satellite":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)

    def display_field_plots(self):
        field_id = self.radio_frame.radio_var.get()
        # The below MUST be changed to query a database
        # The needed values are the PlotIds, the lat, and long of each plot. And more generally, their width, height, and the aisle width
        #Access the database to get the plot ids of the chosen field from the Plot table
        query = select(Plot).where(Plot.locationid == self.radio_frame.radio_var.get())
        result = self.conn.execute(query).scalars().all()
        row_length = 6
        col_length = 5
        for i, row in enumerate(result):
            mydict = {
                        "name" : str(f"Plot #{row.name}"),
                        "plot_id" : row.id,
                        "crop" : "Food",
                        "fertilizer" : "Animal Dung"
                        }
            self.plot_grid.add_plot_to_field(i//row_length, i%col_length, 40, 20, 10, mydict)
    
    def display_graph(self):
        self.figure_frame.lift()
        field_id = self.radio_frame.radio_var.get()
        plot_id = self.plot_grid.plot_var.get()
        values = [(f"{var}", i) for i, var in enumerate(["Yield", "Drought Resistance"])]
        self.var_frame.set_buttons(values)
        self.var_frame.lift()
    
    def display_map(self):
        self.map_widget.lift()
        self.radio_frame.lift()

    def draw_graph(self):
        x = np.arange(0, 100, 5)
        y = np.sin(x) + x
        self.ax.clear()
        self.ax.plot(x, y, 'r-') # Returns a tuple of line objects, thus the comma
        self.ax.scatter(x, x)
        var_1 = self.var_frame.first_clicked._text
        var_2 = self.var_frame.second_clicked._text
        self.ax.set_title(f"Testing correlation between {var_1} and {var_2}")
        self.ax.set_xlabel(var_1)
        self.ax.set_ylabel(var_2)
        self.figure_canvas.draw()

    def on_closing(self, event=0):
        self.destroy()

    def start(self):
        self.mainloop()

def contact_server():
    return []


if __name__ == "__main__":
    app = App()
    app.start()