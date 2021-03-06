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

from gi.repository import Gio, GLib

from urllib.parse import urlparse

from eolie.define import PROXY_BUS, PROXY_PATH


class Server:
    def __init__(self, con, path):
        method_outargs = {}
        method_inargs = {}
        for interface in Gio.DBusNodeInfo.new_for_xml(self.__doc__).interfaces:

            for method in interface.methods:
                method_outargs[method.name] = '(' + ''.join(
                              [arg.signature for arg in method.out_args]) + ')'
                method_inargs[method.name] = tuple(
                                       arg.signature for arg in method.in_args)

            con.register_object(object_path=path,
                                interface_info=interface,
                                method_call_closure=self.on_method_call)

        self.method_inargs = method_inargs
        self.method_outargs = method_outargs

    def on_method_call(self,
                       connection,
                       sender,
                       object_path,
                       interface_name,
                       method_name,
                       parameters,
                       invocation):

        args = list(parameters.unpack())
        for i, sig in enumerate(self.method_inargs[method_name]):
            if sig is 'h':
                msg = invocation.get_message()
                fd_list = msg.get_unix_fd_list()
                args[i] = fd_list.get(args[i])

        try:
            result = getattr(self, method_name)(*args)

            # out_args is atleast (signature1).
            # We therefore always wrap the result as a tuple.
            # Refer to https://bugzilla.gnome.org/show_bug.cgi?id=765603
            result = (result,)

            out_args = self.method_outargs[method_name]
            if out_args != '()':
                variant = GLib.Variant(out_args, result)
                invocation.return_value(variant)
            else:
                invocation.return_value(None)
        except Exception as e:
            pass


class ProxyExtension(Server):
    '''
    <!DOCTYPE node PUBLIC
    '-//freedesktop//DTD D-BUS Object Introspection 1.0//EN'
    'http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd'>
    <node>
    <interface name="org.gnome.Eolie.Proxy">

    <method name="GetForms">
      <arg type="i" name="page_id" direction="in" />
      <arg type="as" name="results" direction="out" />
    </method>

    <signal name='UnsecureFormFocused'>
    </signal>
    </interface>
    </node>
    '''

    def __init__(self, extension, forms):
        """
            Init server
            @param extension as WebKit2WebExtension.WebExtension
            @param forms as FormsExtension
        """
        self.__pages = {}
        self.__forms = forms
        # We cannot use extension.get_page() from here => CRASH
        extension.connect("page-created", self.__on_page_created)
        self.__bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        Gio.bus_own_name_on_connection(self.__bus,
                                       PROXY_BUS,
                                       Gio.BusNameOwnerFlags.NONE,
                                       None,
                                       None)
        Server.__init__(self, self.__bus, PROXY_PATH)

    def GetForms(self, page_id):
        """
            Get password form
            @param page id as int
            @return (username_form, password_form) as (str, str)
        """
        try:
            page = self.__pages[page_id]
            (username, password) = self.__forms.get_forms(page)
            if username is not None and password is not None:
                return (username.get_value(), password.get_value())
        except Exception as e:
            print("ProxyExtension::GetForms():", e)
        return ("", "")

#######################
# PRIVATE             #
#######################
    def __on_focus(self, password, event):
        """
            Emit focus form signal
            @param password as WebKit2WebExtension.DOMHTMLInputElement
            @param event as WebKit2WebExtension.DOMUIEvent
        """
        self.__bus.emit_signal(
                          None,
                          PROXY_PATH,
                          PROXY_BUS,
                          "UnsecureFormFocused",
                          None)

    def __on_document_loaded(self, webpage):
        """
            Check for unsecure content
            @param webpage as WebKit2WebExtension.WebPage
        """
        parsed = urlparse(webpage.get_uri())
        # Check for unsecure content
        if parsed.scheme == "http":
            (username, password) = self.__forms.get_forms(webpage)
            if password is not None:
                password.add_event_listener("focus", self.__on_focus, False)

    def __on_page_created(self, extension, webpage):
        """
            Cache webpage
            @param extension as WebKit2WebExtension
            @param page as WebKit2WebExtension.WebPage
        """
        webpage.connect("document-loaded", self.__on_document_loaded)
        page_id = webpage.get_id()
        self.__pages[page_id] = webpage
