# Copyright (c) 2017 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib

from eolie.menu_history import HistoryMenu
from eolie.define import El


class ToolbarActions(Gtk.Bin):
    """
        Actions toolbar
    """

    def __init__(self, window):
        """
            Init toolbar
            @param window as Window
        """
        Gtk.Bin.__init__(self)
        self.__window = window
        self.__timeout_id = None
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Eolie/ToolbarActions.ui")
        builder.connect_signals(self)

        self.add(builder.get_object("actions"))
        self.set_hexpand(True)
        self.__backward = builder.get_object("back_button")
        self.__forward = builder.get_object("forward_button")
        self.__filter = builder.get_object("filter_button")
        self.__pages_button = builder.get_object("pages_button")

    def set_actions(self, view):
        """
            Set available actions based on view
            @param view as WebView
        """
        self.__backward.set_sensitive(view.can_go_back())
        self.__forward.set_sensitive(view.can_go_forward())

    def backward(self):
        """
            Click next
        """
        self.__window.container.current.webview.go_back()

    def forward(self):
        """
            Click previous
        """
        self.__window.container.current.webview.go_forward()

    @property
    def closed_button(self):
        """
            Get closed pages button
            @return Gtk.MenuButton
        """
        return self.__closed_button

    @property
    def filter_button(self):
        """
            Get filtering toggle button
            @return Gtk.ToggleButton
        """
        return self.__filter

#######################
# PROTECTED           #
#######################
    def _on_back_button_press_event(self, button, event):
        """
            Launch history menu after timeout
            @param button as Gtk.Button
            @param event as Gdk.event
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
        button.get_style_context().set_state(Gtk.StateFlags.ACTIVE)
        self.__window.toolbar.title.hide_popover()
        self.__timeout_id = GLib.timeout_add(500,
                                             self.__on_back_history_timeout)
        if event.button == 3:
            return True

    def _on_back_button_release_event(self, button, event):
        """
            Go backward on current view
            @param button as Gtk.Button
            @param event as Gdk.event
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
            if event.button == 1:
                self.__window.container.current.webview.go_back()
            elif event.button == 2:
                back_list = self.__window.container.\
                    current.webview.get_back_forward_list().get_back_list()
                if back_list:
                    uri = back_list[0].get_uri()
                    self.__window.container.add_web_view(uri, True)
            else:
                self.__on_back_history_timeout()

    def _on_forward_button_press_event(self, button, event):
        """
            Launch history menu after timeout
            @param button as Gtk.Button
            @param event as Gdk.event
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
        button.get_style_context().set_state(Gtk.StateFlags.ACTIVE)
        self.__window.toolbar.title.hide_popover()
        self.__timeout_id = GLib.timeout_add(500,
                                             self.__on_forward_history_timeout)
        if event.button == 3:
            return True

    def _on_forward_button_release_event(self, button, event):
        """
            Go forward on current view
            @param button as Gtk.Button
            @param event as Gdk.event
        """
        if self.__timeout_id is not None:
            GLib.source_remove(self.__timeout_id)
            self.__timeout_id = None
            if event.button == 1:
                self.__window.container.current.webview.go_forward()
            elif event.button == 2:
                forward_list = self.__window.container.\
                    current.webview.get_back_forward_list().get_forward_list()
                if forward_list:
                    uri = forward_list[0].get_uri()
                    self.__window.container.add_web_view(uri, True)
            else:
                self.__on_forward_history_timeout()

    def _on_new_button_clicked(self, button):
        """
            Add a new web view
            @param button as Gtk.Button
        """
        self.__window.container.add_web_view(El().start_page, True)
        self.__window.toolbar.title.hide_popover()

    def _on_pages_button_toggled(self, button):
        """
            Show pages popover
            @param button as Gtk.ToggleButton
        """
        if not button.get_active():
            return
        popover = Gtk.Popover.new_from_model(button, El().pages_menu)
        popover.forall(self.__force_show_image)
        popover.connect("closed",
                        self.__on_pages_popover_closed,
                        button)
        popover.show()

    def _on_filter_button_toggled(self, button):
        """
            Add a new web view
            @param button as Gtk.ToggleButton
        """
        self.__window.container.sidebar.set_filtered(button.get_active())
        self.__window.toolbar.title.hide_popover()

#######################
# PRIVATE             #
#######################
    def __force_show_image(self, widget):
        """
            Little hack to force Gtk.ModelButton to show image
            @param widget as Gtk.Widget
        """
        if isinstance(widget, Gtk.Image):
            GLib.idle_add(widget.show)
        elif hasattr(widget, "forall"):
            GLib.idle_add(widget.forall, self.__force_show_image)

    def __on_pages_popover_closed(self, popover, button):
        """
            Clear menu actions
            @param popover
            @param button as Gtk.ToggleButton
        """
        button.set_active(False)

    def __on_navigation_popover_closed(self, popover, model):
        """
            Clear menu actions
            @param popover
            @param model as HistoryMenu/None
        """
        # Let model activate actions
        GLib.idle_add(model.remove_actions)

    def __on_back_history_timeout(self):
        """
            Show back history
        """
        self.__timeout_id = None
        current = self.__window.container.current.webview
        back_list = current.get_back_forward_list().get_back_list()
        if back_list:
            model = HistoryMenu(El(), back_list)
            popover = Gtk.Popover.new_from_model(self.__backward, model)
            GLib.idle_add(popover.forall, self.__force_show_image)
            popover.connect("closed",
                            self.__on_navigation_popover_closed,
                            model)
            popover.show()

    def __on_forward_history_timeout(self):
        """
            Show forward history
        """
        self.__timeout_id = None
        current = self.__window.container.current.webview
        forward_list = current.get_back_forward_list().get_forward_list()
        if forward_list:
            model = HistoryMenu(El(), forward_list)
            popover = Gtk.Popover.new_from_model(self.__forward, model)
            GLib.idle_add(popover.forall, self.__force_show_image)
            popover.connect("closed",
                            self.__on_navigation_popover_closed,
                            model)
            popover.show()
