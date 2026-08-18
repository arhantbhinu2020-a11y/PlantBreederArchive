import customtkinter as ctk
import tkinter as tk
from tkintermapview import TkinterMapView
from db import Location
from sqlalchemy import select
from tkintermapview.utility_functions import osm_to_decimal
from tktooltip import ToolTip
from ctk_xyframe import CTkXYFrame
import random
import matplotlib
class IntegratedMapView(TkinterMapView):
    def __init__(self, *args, width = 300, height = 200, corner_radius = 0, bg_color = None, database_path = None, use_database_only = False, max_zoom = 19, **kwargs):
        super().__init__(*args, width=width, height=height, corner_radius=corner_radius, bg_color=bg_color, database_path=database_path, use_database_only=use_database_only, max_zoom=max_zoom, **kwargs)
        self.position: tuple[float, float] = (None, None)
        self.update_radio_frame()
    def update_radio_frame(self, attr_name: str = "radio_frame"):
        self.position = self.get_position()
        upper_left, lower_right = self.get_new_bounds()
        print(upper_left, lower_right, self.position)
        # Below MUST be changed to query a geodatabase
        # The list to be returned needs to instead be a tuple of the names and the FieldIds so they can be referenced.
        randbase = random.randint(1, 11)
        values = []
        result = self.master.master.conn.execute(select(Location)).scalars().all()

        values = [(f"{row.name}", row.id) for i, row in enumerate(result)]
        self.master.master.radio_frame.set_buttons(values)
    def mouse_release(self, event):
        super().mouse_release(event)
        pos = self.get_position()
        if pos != self.position: # If the map has moved even slightly, check for new sites in view
            self.update_radio_frame()
    def set_address(self, address_string, marker = False, text = None, **kwargs):
        address_set = super().set_address(address_string, marker, text, **kwargs)
        self.update_radio_frame()
        return address_set
    def get_new_bounds(self):
        upper_left = osm_to_decimal(self.upper_left_tile_pos[0], self.upper_left_tile_pos[1], round(self.zoom))
        lower_right = osm_to_decimal(self.lower_right_tile_pos[0], self.lower_right_tile_pos[1], round(self.zoom))
        return upper_left, lower_right       

class ScrollableRadioFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, title, command = None):
        super().__init__(master, label_text = title)
        self.button_command = command
        self.grid_columnconfigure(0, weight=1)

    def set_buttons(self, values):
        self.radio_var = ctk.IntVar(value = 0)
        self.values = values
        self.buttons: list[ctk.CTkRadioButton] = []
        for i, value in enumerate(self.values):
            button = ctk.CTkRadioButton(self, text=value[0], variable= self.radio_var, value = value[1], command = self.button_command)
            button.grid(row=i, column=0, padx=10, pady=(10, 0), sticky="w")
            self.buttons.append(button)
    
    

class ScrollableCheckboxFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, title, command = None):
        super().__init__(master, label_text = title)
        self.button_command = command
        self.grid_columnconfigure(0, weight=1)

    def set_buttons(self, values):
        self.check_vars: list[ctk.StringVar] = []
        self.values = values
        self.buttons: list[ctk.CTkCheckBox] = []
        self.first_clicked: ctk.CTkCheckBox = None
        self.second_clicked: ctk.CTkCheckBox = None
        for i, value in enumerate(self.values):
            var = ctk.IntVar(value = 0)
            button = ctk.CTkCheckBox(self, text=value[0], variable= var, command = self.on_checkbox_toggle)
            button.grid(row=i, column=0, padx=10, pady=(10, 0), sticky="w")
            self.buttons.append(button)
            self.check_vars.append(var)
    def on_checkbox_toggle(self):
        checked_count = sum(cv.get() for cv in self.check_vars)
        if checked_count >= 2:
            if checked_count >= 3:
                self.first_clicked.deselect()
                self.first_clicked = self.second_clicked
            for i, cv in enumerate(self.check_vars):
                if cv.get() and self.buttons[i] != self.first_clicked:
                    self.second_clicked = self.buttons[i]
                    break
            self.button_command()
        elif checked_count == 1:
            for i, cv in enumerate(self.check_vars):
                if cv.get():
                    self.first_clicked = self.buttons[i]
                    self.second_clicked = None
                    break
        elif checked_count == 0:
            self.first_clicked = None
            self.second_clicked = None

class PlotFrame(ctk.CTkButton):
    def __init__(self, master, width = 140, height = 28, plot_id = -1, corner_radius = None, border_width = None, border_spacing = 2, bg_color = "transparent", fg_color = None, hover_color = None, border_color = None, text_color = None, text_color_disabled = None, background_corner_colors = None, round_width_to_even_numbers = True, round_height_to_even_numbers = True, text = "", font = None, textvariable = None, image = None, state = "normal", hover = True, command = None, compound = "left", anchor = "center", **kwargs):
        super().__init__(master, width, height, corner_radius, border_width, border_spacing, bg_color, fg_color, hover_color, border_color, text_color, text_color_disabled, background_corner_colors, round_width_to_even_numbers, round_height_to_even_numbers, text, font, textvariable, image, state, hover, command, compound, anchor, **kwargs)
        self.plot_id = plot_id
    def _clicked(self, event=None):
        if self._state != tk.DISABLED:

            # click animation: change color with .on_leave() and back to normal after 100ms with click_animation()
            self._on_leave()
            self._click_animation_running = True
            self.after(100, self._click_animation)

            if self._command is not None:
                self._command(self)
class FieldPlotView(CTkXYFrame):
    def __init__(self, master, width = 100, height = 100, scrollbar_width = 16, command = None, scrollbar_fg_color=None, scrollbar_button_color=None, scrollbar_button_hover_color=None, **kwargs):
        super().__init__(master, width, height, scrollbar_width, scrollbar_fg_color, scrollbar_button_color, scrollbar_button_hover_color, **kwargs)
        self.plots: list[PlotFrame] = []
        self.command = command
        self.plot_var = ctk.IntVar(value=0)
    def add_plot_to_field(self, x, y, width, height, aisle, mydata: dict):
        plot = PlotFrame(self, width, height, mydata["plot_id"], command=self.my_command)
        plot.grid(row = y, column = x, padx = (0, aisle), pady = (0, aisle), sticky = "nw")
        ToolTip(plot, f"{mydata['name']}:\n{mydata['crop']} crop w/\n{mydata['fertilizer']}")
        self.plots.append(plot)
    def reset_plots(self):
        for plot in self.plots:
            plot.grid_forget()
        self.plots = []
    def my_command(self, plot: PlotFrame):
        self.plot_var.set(plot.plot_id)
        if self.command:
            self.command()