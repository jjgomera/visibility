#!/usr/bin/python2

import gtk
import gobject
import wnck
import gtk.glade
import os
import sys

# help find the glade file
try:
    os.chdir(os.path.dirname(sys.argv[0]))
except:
    pass


class Visibility:

    def prefs_set(self, prefs):
        """Sets values in the preferences dialog."""

        actions = {
                gtk.CheckButton: 'set_active',
                gtk.SpinButton: 'set_value',
                gtk.HScale: 'set_value',
        }

        # which should we do manually?
        special = ['desktop_names', 'edge', 'substitutions']

        for key, value in prefs.iteritems():
            if key in special:
                continue
            widget = self.prefs.get_widget(key)
            if not widget:
                continue
            action = actions[widget.__class__]
            fn = getattr(widget, action)
            fn(value)

        # desktop names
        desktop_names = ['names', 'numbers', 'none']
        index = desktop_names.index(prefs['desktop_names'])
        self.prefs.get_widget('desktop_names').set_active(index)

        # edge
        edges = ['top_left', 'top_center', 'top_right', 'bottom_left',
                 'bottom_center', 'bottom_right']

        self.prefs.get_widget('edge').set_active(edges.index(prefs['edge']))

    def substitution_init(self):
        self.substitutions = {}
        for k, v in self.config['substitutions'].items():
            self.substitutions[k] = [v]

        size = self.config['icon_size']
        for sub in self.substitutions.values():
            pbuf = gtk.gdk.pixbuf_new_from_file_at_size(sub[0], size, size)
            if len(sub) > 1:
                sub[1] = pbuf
            else:
                sub.append(pbuf)

    def position(self):
        # edges = {'top_left': gtk.gdk.GRAVITY_NORTH_WEST,
        # 'top_center': gtk.gdk.GRAVITY_NORTH,
        # 'top_right': gtk.gdk.GRAVITY_NORTH_EAST,
        # 'bottom_left': gtk.gdk.GRAVITY_SOUTH_WEST,
        # 'bottom_center': gtk.gdk.GRAVITY_SOUTH,
        # 'bottom_right': gtk.gdk.GRAVITY_SOUTH_EAST}

        edge = self.config['edge'].split('_')
        edge_gap_x = self.config['edge_gap_x']
        edge_gap_y = self.config['edge_gap_y']

        self.window.resize(1, 1)
        width, height = self.window.get_size()

        if edge[0] == 'top':
            y = edge_gap_y
        else:
            y = gtk.gdk.screen_height() - height - edge_gap_y

        if edge[1] == 'left':
            x = edge_gap_x
        elif edge[1] == 'center':
            x = (gtk.gdk.screen_width() - width) / 2
        else:
            x = gtk.gdk.screen_width() - width - edge_gap_x

        self.window.move(x, y)

        # self.window.set_gravity(edges[self.config['edge']])

        self.strut_set()

    def strut_unset(self):
        self.window.window.property_delete('_NET_WM_STRUT_PARTIAL')

    def strut_set(self):
        if not self.config['strut']:
            return

        w, h = self.window.get_size()
        x, y = self.window.get_position()

        top = 0
        bottom = 0
        left = 0
        right = 0

        left_start_y = 0
        left_end_y = 0

        right_start_y = 0
        right_end_y = 0

        top_start_x = 0
        top_end_x = 0

        bottom_start_x = 0
        bottom_end_x = 0

        edge = self.config['edge'].split('_')
        # edge_gap_x = self.config['edge_gap_x']
        edge_gap_y = self.config['edge_gap_y']

        if edge[0] == 'top':
            top = h + edge_gap_y
            top_start_x = x
            top_end_x = x + w
        else:
            bottom = h + edge_gap_y
            bottom_start_x = x
            bottom_end_x = x + w
        """
        if edge[1] == 'left':
            left = w + edge_gap
            left_start_y = y
            left_end_y = y + h
        else:
            right = w + edge_gap
            right_start_y = y
            right_end_y = y + h
        """
        if self.window.window:
            self.window.window.property_change(
                '_NET_WM_STRUT_PARTIAL', 'CARDINAL', 32,
                gtk.gdk.PROP_MODE_REPLACE,
                [left, right, top, bottom, left_start_y, left_end_y,
                 right_start_y, right_end_y, top_start_x, top_end_x,
                 bottom_start_x, bottom_end_x])

    def pref_dialog_init(self):
        self.prefs = gtk.glade.XML('visibility.glade')
        # set defaults
        self.prefs_set(self.config)
        self.prefs.signal_autoconnect(self)

    def resized(self, window, params):
        if self.ignore_resize:
            self.ignore_resize = False
            return

        self.ignore_resize = True
        self.position()

    def __init__(self):
        self.config = {
                "separation": 10,
                "spacing": 5,
                "border": 5,
                "desktop_names": "names",
                "inactive_alpha": 0.5,
                "minimized_alpha": 0.3,
                "edge": "bottom_right",
                "edge_gap_x": 10,
                "edge_gap_y": 10,
                "icon_size": 20,
                "substitutions": {},
                "strut": False
        }

        self.substitutions = {}
        self.ignore_resize = False

        self.disp = gtk.gdk.display_get_default().get_name()
        self.cfgdir = "%s/.config/visibility" % os.getenv('HOME')
        self.cfgfile = "%s/config-%s" % (self.cfgdir, self.disp)

        try:
            file = open(self.cfgfile, 'r')
            self.config.update(eval("\n".join(file.readlines())))
            file.close()
        except:
            pass

        self.substitution_init()

        self.window = gtk.Window()

        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
        self.window.connect('configure-event', self.resized)

        self.container = gtk.HBox(False, self.config['separation'])
        self.window.add(self.container)
        self.window.stick()
        self.window.set_border_width(self.config['border'])

        self.workspaces = {}
        self.windows = {}
        self.windows_needing_attention = {}

        self.tooltips = gtk.Tooltips()

        self.oldconfig = self.config.copy()

        self.pref_dialog_init()

    def revert_clicked_cb(self, widget):
        self.prefs_set(self.oldconfig)

    def preferences_close_cb(self, widget):
        # this is invoked when you close the dialog without clicking ok
        self.pref_dialog_init()

    def separation_value_changed_cb(self, widget):
        self.config['separation'] = int(widget.get_value())
        self.container.set_spacing(self.config['separation'])
        self.window.resize(1, 1)

    def spacing_value_changed_cb(self, widget):
        self.config['spacing'] = int(widget.get_value())
        for workspace in self.workspaces.values():
            workspace[0].set_spacing(self.config['spacing'])

        self.window.resize(1, 1)

    def border_value_changed_cb(self, widget):
        self.config['border'] = int(widget.get_value())
        self.window.set_border_width(self.config['border'])
        self.window.resize(1, 1)

    def icon_size_value_changed_cb(self, widget):
        self.config['icon_size'] = int(widget.get_value())
        self.substitution_init()

        for window in self.windows:
            self.window_icon_changed(window)

    def inactive_alpha_value_changed_cb(self, widget):
        self.config['inactive_alpha'] = widget.get_value()
        for window in self.windows:
            self.window_icon_changed(window)

    def minimized_alpha_value_changed_cb(self, widget):
        self.config['minimized_alpha'] = widget.get_value()
        # XXX: HOW DO I KNOW WHAT TO DO??? WHAT HAS SCIENCE DONE
        for window in self.windows:
            self.window_icon_changed(window)

    def edge_changed_cb(self, widget):
        edge = widget.get_active_text().lower().replace(' ', '_')
        self.config['edge'] = edge
        self.position()

    def desktop_names_changed_cb(self, widget):
        names = self.config['desktop_names'] = widget.get_active_text().lower()
        if names == "none":
            for workspace in self.workspaces.values():
                workspace[0].get_children()[0].hide()
        elif names == "names":
            for space, workspace in self.workspaces.iteritems():
                label = workspace[0].get_children()[0]
                label.get_children()[0].set_markup(
                    "<b>%s:</b>" % space.get_name())
                label.show_all()
        elif names == "numbers":
            for space, workspace in self.workspaces.iteritems():
                label = workspace[0].get_children()[0]
                label.get_children()[0].set_markup(
                    "<b>%s:</b>" % (space.get_number() + 1))
                label.show_all()

        self.window.resize(1, 1)

    def edge_gap_value_changed_cb(self, widget):
        self.config[widget.get_name()] = int(widget.get_value())
        self.position()

    def strut_toggled_cb(self, widget):
        self.config['strut'] = widget.get_active()
        if self.config['strut']:
            self.strut_set()
        else:
            self.strut_unset()

    def ok_clicked_cb(self, widget):
        # save cfg
        disp = gtk.gdk.display_get_default().get_name()
        cfgdir = "%s/.config/visibility" % os.getenv('HOME')

        try:
            os.makedirs(cfgdir)
        except:
            pass

        file = open("%s/config-%s" % (cfgdir, disp), 'w')

        file.writelines(str(self.config))
        file.close()

        self.prefs.get_widget('preferences').hide()

        self.oldconfig = self.config.copy()

    def window_get_class_hint(self, window):
        gdkwin = gtk.gdk.window_foreign_new(window.get_xid())
        prop = gdkwin.property_get('WM_CLASS')
        if not prop:
            return None
        prop = prop[2].split("\x00")
        return prop[0:2]

    def window_icon_is_substituted(self, window):
        prop = self.window_get_class_hint(window)

        if not prop:
            return False

        try:
            sol = ".".join(prop)
            ary = self.substitutions[sol]
        except KeyError:
            try:
                sol = prop[0]
                ary = self.substitutions[sol]
            except KeyError:
                try:
                    sol = prop[1]
                    ary = self.substitutions[sol]
                except KeyError:
                    return False

        return [sol, ary]

    def window_get_icon(self, window):
        size = self.config['icon_size']

        ary = self.window_icon_is_substituted(window)

        if not ary:
            return window.get_icon().scale_simple(
                size, size, gtk.gdk.INTERP_BILINEAR)
        else:
            return ary[1][1]

    def workspace_context_menu(self, button, space):
        menu = gtk.Menu()

        item = gtk.ImageMenuItem(gtk.STOCK_JUMP_TO)
        item.connect('activate', lambda w: space.activate(0))
        item.show()
        menu.append(item)

        separator = gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        preferences = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        preferences.connect(
            'activate', lambda w: self.prefs.get_widget('preferences').show())
        preferences.show()
        menu.append(preferences)

        return menu

    def workspace_add(self, screen, space):
        workspace = gtk.HBox(False, self.config['spacing'])

        string = space.get_name()
        if self.config['desktop_names'] == 'numbers':
            string = str(space.get_number() + 1)

        label = gtk.Label("<b>%s:</b>" % string)
        label.set_use_markup(True)

        if screen.get_active_workspace() == space:
            self.workspace_active = space
        else:
            label.set_sensitive(False)

        def name_changed(space):
            if self.config['desktop_names'] == 'names':
                label.set_markup("<b>%s:</b>" % space.get_name())

            self.window.resize(1, 1)

        space.connect('name-changed', name_changed)

        event = gtk.EventBox()
        event.set_name(str(space.get_number() + 1))
        event.add(label)

        def button_release_cb(button, event):
            if event.button == 1:
                space.activate(0)
                return

            self.workspace_context_menu(button, space).popup(
                None, None, None, event.button, event.get_time())

        event.connect('button_release_event', button_release_cb)

        workspace.pack_start(event)

        if self.config['desktop_names'] != 'none':
            event.show_all()

        separator = None

        if len(self.workspaces) > 0:
            separator = gtk.VSeparator()
            self.container.pack_start(separator)
            separator.show()

        self.workspaces[space] = [workspace, separator]

        self.container.pack_start(workspace)
        workspace.show()
        visibility.strut_set()

    def workspace_remove(self, screen, space):
        self.workspaces[space][0].destroy()
        self.workspaces[space][1].destroy()
        self.window.resize(1, 1)
        del self.workspaces[space]
        visibility.strut_set()

    def substitute(self, button, widget):
        window = wnck.window_get(int(widget.get_name()))
        prop = self.window_get_class_hint(window)
        if not prop:
            dialog = self.prefs.get_widget('unsubstitutable')
            if not dialog:
                self.pref_dialog_init()
                dialog = self.prefs.get_widget('unsubstitutable')

            text = dialog.get_property('secondary-text')
            dialog.format_secondary_text(text.replace('%s', window.get_name()))
            dialog.connect('response', lambda w, r: w.destroy())
            dialog.run()
            return

        cls = ".".join(prop)

        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, gtk.STOCK_OK,
                   gtk.RESPONSE_ACCEPT)
        dialog = gtk.FileChooserDialog("Pick an icon", buttons=buttons)
        dialog.connect('response', lambda d, l: d.hide())
        response = dialog.run()

        if response != gtk.RESPONSE_ACCEPT:
            return

        self.config['substitutions'][cls] = dialog.get_filename()
        self.ok_clicked_cb(None)  # save
        self.substitution_init()

    def unsubstitute(self, button, key):
        del self.config['substitutions'][key]
        self.ok_clicked_cb(None)  # save
        self.substitution_init()

    def window_context_menu(self, widget):
        menu = gtk.Menu()

        window = wnck.window_get(int(widget.get_name()))

        if window.is_maximized():
            item = gtk.ImageMenuItem(gtk.STOCK_ZOOM_OUT)
            item.get_children()[0].set_label('_Restore')
            item.connect('activate',
                         (lambda button, window: window.unmaximize()), window)
        else:
            item = gtk.ImageMenuItem(gtk.STOCK_ZOOM_100)
            item.get_children()[0].set_label('_Maximize')
            item.connect('activate',
                         (lambda button, window: window.maximize()), window)

        item.show()
        menu.append(item)

        if window.is_minimized():
            item = gtk.ImageMenuItem(gtk.STOCK_REDO)
            item.get_children()[0].set_label('_Unminimize')
            item.connect('activate',
                         (lambda button, window: window.unminimize(0)), window)
        else:
            item = gtk.ImageMenuItem(gtk.STOCK_UNDO)
            item.get_children()[0].set_label('M_inimize')
            item.connect('activate',
                         (lambda button, window: window.minimize()), window)

        item.show()
        menu.append(item)

        item = gtk.ImageMenuItem(gtk.STOCK_CLOSE)
        item.connect('activate',
                     (lambda button, window: window.close(0)), window)
        item.show()
        menu.append(item)

        separator = gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        substitute = gtk.ImageMenuItem(gtk.STOCK_SELECT_COLOR)
        substitute.get_children()[0].set_label('_Substitute')
        substitute.connect('activate', self.substitute, widget)
        menu.append(substitute)
        substitute.show()

        ary = self.window_icon_is_substituted(
            wnck.window_get(int(widget.get_name())))

        if ary:
            unsubstitute = gtk.ImageMenuItem(gtk.STOCK_CLEAR)
            unsubstitute.get_children()[0].set_label('_Remove Substitution')
            unsubstitute.connect('activate', self.unsubstitute, ary[0])
            unsubstitute.show()
            menu.append(unsubstitute)

        separator = gtk.SeparatorMenuItem()
        separator.show()
        menu.append(separator)

        preferences = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        preferences.connect('activate', lambda w:
                            self.prefs.get_widget('preferences').show())
        preferences.show()
        menu.append(preferences)
        return menu

    def icon_clicked_cb(self, widget, event):
        if event.button == 1:
            window = wnck.window_get(int(widget.get_name()))
            if self.window_active == window:
                window.minimize()
            else:
                window.get_workspace().activate(event.get_time())
                window.activate(event.get_time())
        else:
            self.window_context_menu(widget).popup(
                None, None, None, event.button, event.get_time())

    def icon_hover_cb(self, widget, event):
        window = wnck.window_get(int(widget.get_name()))
        pbuf = self.window_get_icon(window)
        image = widget.get_children()[0]
        self.hover = image.get_pixbuf()
        image.set_from_pixbuf(pbuf)

    def icon_unhover_cb(self, widget, event):
        image = widget.get_children()[0]
        image.set_from_pixbuf(self.hover)

    def window_add(self, window):
        pbuf = self.window_get_icon(window).copy()
        if window.is_minimized():
            pbuf = self.pixbuf_tint(pbuf, self.config['minimized_alpha'])
        elif window.is_active():
            self.window_active = window
        else:
            pbuf = self.pixbuf_tint(pbuf, self.config['inactive_alpha'])

        def window_add(window, workspace):
            icon = gtk.Image()
            icon.set_from_pixbuf(pbuf)
            button = gtk.EventBox()

            button.set_name(str(window.get_xid()))
            button.add(icon)
            button.connect('button_release_event', self.icon_clicked_cb)
            button.connect('enter-notify-event', self.icon_hover_cb)
            button.connect('leave-notify-event', self.icon_unhover_cb)

            self.tooltips.set_tip(button, window.get_name())

            self.workspaces[workspace][0].pack_start(button)

            # display if necessary! lawl
            if not window.is_skip_pager():
                icon.show()
                button.show()

            return button

        workspace = window.get_workspace()

        buttons = []

        if workspace:
            buttons.append(window_add(window, workspace))
        else:
            for workspace in self.workspaces:
                buttons.append(window_add(window, workspace))

        button = buttons[0]
        self.windows[window] = [buttons, window.get_workspace()]

        # XXX: this works only for newly opened windows, fix it
        # (it's because our window has yet to map)
        icon = button.get_children()[0]
        if icon.window:
            x, y = icon.window.get_origin()
            # print "%d %d" % (x, y)
            window.set_icon_geometry(
                x, y, button.allocation.width, button.allocation.height)

    def window_remove(self, window):
        try:
            wn = self.windows[window]
            for button in wn[0]:
                button.destroy()
        except:
            pass

        # get to smallest size possible
        self.window.resize(1, 1)

    def window_workspace_changed(self, window):
        # xxx: doesn't this lack intelligence?
        self.window_remove(window)
        self.window_add(window)

    def window_name_changed(self, window):
        buttons = self.windows[window][0]
        for button in buttons:
            self.tooltips.set_tip(button, window.get_name())

    def window_needs_attention(self, window):
        max = 30
        stop = False
        if window in self.windows_needing_attention:
            status, number = self.windows_needing_attention[window]

            if number >= max:
                stop = True
                # reset the icon
                if window.is_active():
                    status = False
                else:
                    status = True

            status = not status
            self.windows_needing_attention[window] = [status, number + 1]
        else:
            self.windows_needing_attention[window] = [True, 1]
            status = True

        pbuf = self.window_get_icon(window).copy()
        if not status:
            pbuf = self.pixbuf_tint(pbuf, self.config['inactive_alpha'])

        buttons = self.windows[window][0]
        for button in buttons:
            button.get_children()[0].set_from_pixbuf(pbuf)

        if stop:
            del self.windows_needing_attention[window]

        return not stop

    def window_state_changed(self, window, oldstate, newstate):
        if (oldstate & wnck.WINDOW_STATE_SKIP_PAGER) and not \
                (newstate & wnck.WINDOW_STATE_SKIP_PAGER):
            for button in self.windows[window][0]:
                button.show_all()
        elif (newstate & wnck.WINDOW_STATE_SKIP_PAGER):
            for button in self.windows[window][0]:
                button.hide()

        if window.needs_attention():
            if window not in self.windows_needing_attention:
                gobject.timeout_add(200, self.window_needs_attention, window)

        # retardedly accounts for minimization
        self.window_icon_changed(window)

    def pixbuf_tint(self, pixbuf, fraction):
        w = pixbuf.get_width()
        h = pixbuf.get_height()
        blank = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, w, h)
        blank.fill(0)

        pixbuf.composite(blank, 0, 0, w, h, 0, 0, 1, 1,
                         gtk.gdk.INTERP_NEAREST, int(fraction * 255.0))
        return blank

    def window_icon_changed(self, window):
        # xxx: doesn't this lack intelligence?
        pos = -1
        if window.get_workspace():  # not sticky
            widget = self.windows[window][0][0]
            pos = widget.get_parent().get_children().index(widget)

        self.window_remove(window)
        self.window_add(window)
        if pos != -1:
            widget = self.windows[window][0][0]
            widget.get_parent().reorder_child(widget, pos)

    def workspace_active_changed(self, screen, previous):
        try:
            w = self.workspaces[self.workspace_active][0]
            w.get_children()[0].get_children()[0].set_sensitive(False)
        except AttributeError:
            pass

        self.workspace_active = screen.get_active_workspace()
        w = self.workspaces[self.workspace_active][0]
        w.get_children()[0].get_children()[0].set_sensitive(True)

    def window_active_changed(self, screen, previous):
        try:
            pbuf = self.window_get_icon(self.window_active).copy()
            if self.window_active.is_minimized():
                pbuf = self.pixbuf_tint(pbuf, self.config['minimized_alpha'])
            else:
                pbuf = self.pixbuf_tint(pbuf, self.config['inactive_alpha'])
            for button in self.windows[self.window_active][0]:
                button.get_children()[0].set_from_pixbuf(pbuf)
        except AttributeError:
            pass
        except KeyError:
            pass
        except IndexError:
            pass  # this happens when you close the active window

        self.window_active = screen.get_active_window()

        if self.window_active is None:
            return

        pbuf = self.window_get_icon(self.window_active)
        for button in self.windows[self.window_active][0]:
            button.get_children()[0].set_from_pixbuf(pbuf)

    def show(self):
        self.container.show()
        self.window.show()

visibility = Visibility()

screen = wnck.screen_get_default()
screen.force_update()
windows = screen.get_windows()


def window_opened(screen, window):
    window.connect('workspace-changed', visibility.window_workspace_changed)
    window.connect('name-changed', visibility.window_name_changed)
    window.connect('state-changed', visibility.window_state_changed)
    window.connect('icon-changed', visibility.window_icon_changed)
    visibility.window_add(window)
    visibility.strut_set()


def window_closed(screen, window):
    visibility.window_remove(window)
    del visibility.windows[window]
    visibility.strut_set()


# begin 'main' here

gtk.gdk.error_trap_push()  # silently ignore x errors like a pro

screen.connect('window-opened', window_opened)
screen.connect('window-closed', window_closed)
screen.connect('active-window-changed', visibility.window_active_changed)
screen.connect('active-workspace-changed', visibility.workspace_active_changed)
screen.connect('workspace-created', visibility.workspace_add)
screen.connect('workspace-destroyed', visibility.workspace_remove)

for i in range(0, screen.get_workspace_count()):
    visibility.workspace_add(screen, screen.get_workspace(i))

for window in windows:
    window_opened(screen, window)

visibility.show()
visibility.position()

gtk.main()
