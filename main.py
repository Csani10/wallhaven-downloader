import sys
from pathlib import Path
import gi
import json

# Specify required library versions before importing from gi.repository
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gio
from wallhaven_api import WallhavenAPI, WallhavenSearchFilters, WallhavenResolutionSearchType, WallhavenSorting, WallhavenOrder, TOP_RANGE, PRESET_RESOLUTIONS, ALLOWED_COLORS, ASPECT_RATIOS

Adw.init()

class AppConfig:
    CONFIG_PATH = Path.home() / ".config" / "wallhaven-downloader" / "config.json"
    
    DEFAULT_CONFIG = {
        "api_key": "",
        "download_path": str(Path.home() / "Pictures" / "Wallpapers")
    }

    def __init__(self):
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.data = self.load()

    def load(self) -> dict:
        self.data = {}

        if not self.CONFIG_PATH.exists():
            self.save(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**self.DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            return self.DEFAULT_CONFIG.copy()

    def save(self, new_data: dict = None):
        if new_data:
            self.data.update(new_data)
        with open(self.CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    @property
    def api_key(self) -> str:
        return self.data.get("api_key", "")

    @property
    def download_path(self) -> str:
        return self.data.get("download_path", "")

class WallpaperInfoPage(Adw.NavigationPage):
    def __init__(self, api: WallhavenAPI, wallpaper_id, **kwargs):
        super().__init__()
        self.set_title("Wallpaper info")
        self.set_tag("wallinfo-page")

        self.api = api
        self.wallpaper_id = wallpaper_id

        self.info = self.api.get_wallpaper_info(wallpaper_id)

        adw_toolbar_view = Adw.ToolbarView.new()
        self.set_child(child=adw_toolbar_view)

        adw_header_bar = Adw.HeaderBar.new()
        adw_toolbar_view.add_top_bar(widget=adw_header_bar)

        # 1. Create the ToastOverlay container
        self.toast_overlay = Adw.ToastOverlay()

        if not self.info:
            label = Gtk.Label(label=f"Error getting info for wallpaper id: {self.wallpaper_id}")
            self.toast_overlay.set_child(label)
        else:
            paned = Gtk.Paned(
                orientation=Gtk.Orientation.HORIZONTAL,
                margin_top=20,
                margin_bottom=20,
                margin_end=20,
                margin_start=20
            )

            # Left side: Sidebar for info
            info_window = Gtk.ScrolledWindow()
            info_window.set_size_request(200, -1)
            info_window.set_vexpand(True)

            info_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=12
            )

            id_label = Gtk.Label(label=f"ID: {self.wallpaper_id}")
            res_label = Gtk.Label(label=f"Resolution: {self.info.resolution}")
            
            id_label.set_halign(Gtk.Align.START)
            res_label.set_halign(Gtk.Align.START)

            download_button = Gtk.Button(label="Download", css_classes=["suggested-action"])
            download_button.set_halign(Gtk.Align.START)
            download_button.connect("clicked", self.on_download)

            info_box.append(id_label)
            info_box.append(res_label)
            info_box.append(download_button)

            info_window.set_child(info_box)

            # Right side: Picture area
            img_path = str(self.info.download_to_folder(self.api.temp_path).absolute())
            picture = Gtk.Picture.new_for_filename(img_path)
            
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_margin_start(20)
            
            picture.set_hexpand(True)
            picture.set_vexpand(True)

            paned.set_start_child(info_window)
            paned.set_end_child(picture)
            paned.set_shrink_start_child(False)
            paned.set_shrink_end_child(False)

            paned.set_position(230)

            # 2. Place the paned view inside the ToastOverlay
            self.toast_overlay.set_child(paned)

        # 3. Set the ToastOverlay as the content of the ToolbarView
        adw_toolbar_view.set_content(self.toast_overlay)

    def on_download(self, widget):
        try:
            self.info.download_to_folder(self.api.download_path)
            toast = Adw.Toast.new(f"Downloaded wallpaper #{self.wallpaper_id}")
            toast.set_timeout(3)
            self.toast_overlay.add_toast(toast)
        except Exception as e:
            toast = Adw.Toast.new(f"Failed to download: {e}")
            self.toast_overlay.add_toast(toast)

class MultiSelectRow(Adw.ExpanderRow):
    __gsignals__ = {
        # Signal emitted whenever selection changes, passing the list of selected items
        'changed': (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }

    def __init__(self, title: str, options: list[str], selected_options: list[str] = None, set_subtitles=True, **kwargs):
        super().__init__(title=title, **kwargs)

        self.options = options
        self.selected = set(selected_options or [])
        self._switches = {}
        self.set_subtitles = set_subtitles

        self._update_subtitle()

        # Build a SwitchRow for each selectable option
        for option in self.options:
            switch_row = Adw.SwitchRow(title=option)
            is_active = option in self.selected
            switch_row.set_active(is_active)
            
            # Connect toggle event
            switch_row.connect("notify::active", self._on_switch_toggled, option)
            
            self.add_row(switch_row)
            self._switches[option] = switch_row

    def _on_switch_toggled(self, switch_row, pspec, option):
        if switch_row.get_active():
            self.selected.add(option)
        else:
            self.selected.discard(option)

        self._update_subtitle()
        self.emit("changed", self.get_selected())

    def _update_subtitle(self):
        """Updates the row subtitle to summarize active selections."""
        if not self.set_subtitles:
            return

        if not self.selected:
            self.set_subtitle("None")
        else:
            self.set_subtitle(", ".join(self.selected))

    def get_selected(self) -> list[str]:
        """Returns currently active items as a list of strings."""
        return list(self.selected)

class ComboOption(GObject.Object):
    def __init__(self, item_id: str, label: str):
        super().__init__()
        self._id = item_id
        self._label = label

    @GObject.Property(type=str)
    def id(self):
        return self._id

    @GObject.Property(type=str)
    def label(self):
        return self._label

class ColorGridSelect(Gtk.Box):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }

    def __init__(self, colors: list[str], selected_colors: list[str] = None, title: str = "", **kwargs):
        """
        colors: List of (HEX/CSS_COLOR, NAME) tuples e.g., [("660000", "Red"), ("006600", "Green")]
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6, **kwargs)

        self.selected = set(selected_colors or [])
        self._buttons = {}

        if title != "":
            label = Gtk.Label(label=title)
            label.set_margin_top(5)
            self.append(label)

        # FlowBox grid container
        self.flowbox = Gtk.FlowBox(
            valign=Gtk.Align.START,
            max_children_per_line=8,
            min_children_per_line=4,
            selection_mode=Gtk.SelectionMode.NONE,
            row_spacing=8,
            column_spacing=8,
        )
        self.append(self.flowbox)

        # Build swatch buttons
        for color_hex in colors:
            btn = self._create_color_button(color_hex)
            self.flowbox.append(btn)
            self._buttons[color_hex] = btn

    def _create_color_button(self, hex_code: str) -> Gtk.ToggleButton:
        btn = Gtk.ToggleButton()
        btn.set_size_request(36, 36)

        # Apply CSS for solid color block and rounded corners
        css = f"""
            button.color-swatch-{hex_code} {{
                background-color: #{hex_code};
                border-radius: 8px;
                border: 1px solid rgba(0,0,0,0.2);
                padding: 0px;
            }}
            button.color-swatch-{hex_code}:checked {{
                border: 2px solid white;
                outline: 2px solid var(--accent-bg-color);  /* <--- Use var(--accent-bg-color) */
            }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        btn.get_style_context().add_provider(
            provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        btn.add_css_class(f"color-swatch-{hex_code}")

        # Checkmark icon overlay when selected
        icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
        icon.set_visible(hex_code in self.selected)
        btn.set_child(icon)

        # Restore initial state
        btn.set_active(hex_code in self.selected)

        # Connect toggle handler
        btn.connect("toggled", self._on_button_toggled, hex_code, icon)
        return btn

    def _on_button_toggled(self, btn, hex_code: str, icon: Gtk.Image):
        is_active = btn.get_active()
        icon.set_visible(is_active)

        if is_active:
            self.selected.add(hex_code)
        else:
            self.selected.discard(hex_code)

        self.emit("changed", self.get_selected())

    def get_selected(self) -> list[str]:
        return sorted(list(self.selected))

class FiltersDialog(Adw.Dialog):
    def __init__(self, current_filters: WallhavenSearchFilters, **kwargs):
        super().__init__(**kwargs)

        self.set_title("Search Filters")
        self.set_content_width(400)
        self.set_content_height(480)

        self.filters = current_filters

        adw_toolbar_view = Adw.ToolbarView.new()
        self.set_child(child=adw_toolbar_view)

        adw_header_bar = Adw.HeaderBar.new()
        adw_toolbar_view.add_top_bar(widget=adw_header_bar)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.close())
        adw_header_bar.pack_start(cancel_btn)

        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("suggested-action")
        apply_btn.connect("clicked", self.on_apply)
        adw_header_bar.set_show_end_title_buttons(False)
        adw_header_bar.pack_end(apply_btn)

        pref_page = Adw.PreferencesPage()
        pref_group = Adw.PreferencesGroup(title="Search Settings")
        pref_page.add(pref_group)

        self.category_row = MultiSelectRow(
            title="Categories",
            options=self.filters.categories.as_list(),
            selected_options=self.filters.categories.selected_as_list(),
        )
        pref_group.add(self.category_row)

        self.purity_row = MultiSelectRow(
            title="Purity",
            options=self.filters.purity.as_list(),
            selected_options=self.filters.purity.selected_as_list()
        )
        pref_group.add(self.purity_row)

        sorting_store = Gio.ListStore.new(ComboOption)
        sorting_store.append(ComboOption("relevance", "Relevance"))
        sorting_store.append(ComboOption("random", "Random"))
        sorting_store.append(ComboOption("date_added", "Date Added"))
        sorting_store.append(ComboOption("views", "Views"))
        sorting_store.append(ComboOption("favourites", "Favourites"))
        sorting_store.append(ComboOption("toplist", "Toplist"))
        sorting_store.append(ComboOption("hot", "Hot"))
        self.sorting_row = Adw.ComboRow(title="Sort by")
        self.sorting_row.set_model(sorting_store)
        self.sorting_row.set_selected(self.filters.sorting.str_to_idx(self.filters.sorting.value))

        expression = Gtk.PropertyExpression.new(ComboOption, None, "label")
        self.sorting_row.set_expression(expression)
        pref_group.add(self.sorting_row)

        order_store = Gio.ListStore.new(ComboOption)
        order_store.append(ComboOption("asc", "Ascending"))
        order_store.append(ComboOption("desc", "Descending"))
        self.order_row = Adw.ComboRow(title="Order")
        self.order_row.set_model(order_store)
        self.order_row.set_selected(self.filters.order.str_to_idx(self.filters.order.value))

        expression = Gtk.PropertyExpression.new(ComboOption, None, "label")
        self.order_row.set_expression(expression)
        pref_group.add(self.order_row)

        self.toplist_range = Adw.ComboRow(
            title="Toplist range",
            model=Gtk.StringList.new(TOP_RANGE),
            selected=TOP_RANGE.index(self.filters.toplist_range)
        )
        pref_group.add(self.toplist_range)

        self.resolution_type = Adw.ComboRow(
            title="Resolution search type",
            model=Gtk.StringList.new(["Atleast", "Exact", "All"]),
            selected=self.filters.resolution_search_type.value
        )
        pref_group.add(self.resolution_type)

        self.resolutions_row = MultiSelectRow(
            title="Resolutions",
            subtitle="Only used if resolution type set to exact",
            options=PRESET_RESOLUTIONS,
            selected_options=self.filters.resolutions,
            set_subtitles=False,
        )
        pref_group.add(self.resolutions_row)

        self.resolution_atleast_row = Adw.ComboRow(
            title="Resolution atleast",
            model=Gtk.StringList.new(PRESET_RESOLUTIONS),
            selected=PRESET_RESOLUTIONS.index(self.filters.atleast) if self.filters.atleast in PRESET_RESOLUTIONS else 0
        )
        pref_group.add(self.resolution_atleast_row)

        self.custom_resolution_row = Adw.EntryRow(
            title="Custom resolution"
        )
        if self.filters.resolution_search_type == WallhavenResolutionSearchType.ATLEAST:
            if self.filters.atleast not in PRESET_RESOLUTIONS: self.custom_resolution_row.set_text(self.filters.atleast)
        elif self.filters.resolution_search_type == WallhavenResolutionSearchType.EXACT:
            for res in self.filters.resolutions:
                if res not in PRESET_RESOLUTIONS: self.custom_resolution_row.set_text(res)
        pref_group.add(self.custom_resolution_row)

        self.ratios_row = MultiSelectRow(
            title="Allowed ratios",
            options=ASPECT_RATIOS,
            selected_options=self.filters.ratios
        )
        pref_group.add(self.ratios_row)

        self.color_select = ColorGridSelect(
            colors=ALLOWED_COLORS,
            selected_colors=self.filters.colors,
            title="Colors"
        )

        color_row = Adw.ActionRow()
        color_row.set_child(self.color_select)
        pref_group.add(color_row)

        adw_toolbar_view.set_content(pref_page)

    def on_apply(self, widget):
        self.filters.categories.general = "General" in self.category_row.get_selected()
        self.filters.categories.anime = "Anime" in self.category_row.get_selected()
        self.filters.categories.people = "People" in self.category_row.get_selected()

        self.filters.purity.sfw = "SFW" in self.purity_row.get_selected()
        self.filters.purity.sketchy = "Sketchy" in self.purity_row.get_selected()
        self.filters.purity.nsfw = "NSFW" in self.purity_row.get_selected()

        self.filters.sorting = list(WallhavenSorting)[self.sorting_row.get_selected()]

        self.filters.order = list(WallhavenOrder)[self.order_row.get_selected()]

        self.filters.toplist_range = TOP_RANGE[self.toplist_range.get_selected()]

        self.filters.resolution_search_type = list(WallhavenResolutionSearchType)[self.resolution_type.get_selected()]

        self.filters.resolutions = self.resolutions_row.get_selected()

        self.filters.atleast = PRESET_RESOLUTIONS[self.resolution_atleast_row.get_selected()]

        if self.filters.resolution_search_type == WallhavenResolutionSearchType.ATLEAST:
            self.filters.atleast = self.custom_resolution_row.get_text().strip()
        elif self.filters.resolution_search_type == WallhavenResolutionSearchType.EXACT:
            self.filters.resolutions.append(self.custom_resolution_row.get_text().strip())

        self.filters.ratios = self.ratios_row.get_selected()

        self.filters.colors = self.color_select.get_selected()

        self.emit("applied", self.filters)
        self.close()

GObject.signal_new("applied", FiltersDialog, GObject.SignalFlags.RUN_FIRST, None, (object,))

class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, config: AppConfig, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Preferences")
        self.config = config

        page = Adw.PreferencesPage()
        self.add(page)

        api_group = Adw.PreferencesGroup(
            title="Wallhaven API",
            description="API key for accessing NSFW and restricted content"
        )
        page.add(api_group)

        self.api_key_entry = Adw.PasswordEntryRow(title="API Key")
        self.api_key_entry.set_text(self.config.api_key)
        self.api_key_entry.connect("changed", self._on_api_key_changed)
        api_group.add(self.api_key_entry)

        download_group = Adw.PreferencesGroup(title="Downloads")
        page.add(download_group)

        self.download_path_row = Adw.ActionRow(
            title="Download Folder",
            subtitle=self.config.download_path
        )

        folder_btn = Gtk.Button(icon_name="folder-open-symbolic")
        folder_btn.set_valign(Gtk.Align.CENTER)
        folder_btn.connect("clicked", self._on_select_folder)
        
        self.download_path_row.add_suffix(folder_btn)
        download_group.add(self.download_path_row)

    def _on_api_key_changed(self, entry):
        """Saves API key as the user types."""
        self.config.save({"api_key": entry.get_text().strip()})

    def _on_select_folder(self, button):
        """Opens GTK4 file dialog to choose download destination."""
        dialog = Gtk.FileDialog(title="Select Download Folder")
        
        # Open folder picker modally over the PreferencesDialog
        dialog.select_folder(self.get_root(), None, self._on_folder_selected)

    def _on_folder_selected(self, dialog, result):
        try:
            folder_file = dialog.select_folder_finish(result)
            if folder_file:
                selected_path = folder_file.get_path()
                self.config.save({"download_path": selected_path})
                self.download_path_row.set_subtitle(selected_path)
        except Exception as e:
            print(f"Folder selection cancelled or failed: {e}")
        dialog = Gtk.FileChooserDialog()

class MainPage(Adw.NavigationPage):
    def __init__(self, api, adw_navigation_page, **kwargs):
        super().__init__()
        self.set_title("Wallhaven Downloader")
        self.set_tag("main-page")

        self.adw_navigation_page = adw_navigation_page
        self.api = api
        self.current_filters = WallhavenSearchFilters()

        adw_toolbar_view = Adw.ToolbarView.new()
        self.set_child(child=adw_toolbar_view)

        adw_header_bar = Adw.HeaderBar.new()
        adw_toolbar_view.add_top_bar(widget=adw_header_bar)


        # ----------------------------------------------------
        # 1. Create Search Widgets & Add to HeaderBar
        # ----------------------------------------------------
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search wallpapers...")
        self.search_entry.set_text("")  # Default initial query
        
        # Trigger search when user presses Enter inside the search entry
        self.search_entry.connect("activate", self.on_search_triggered)

        search_button = Gtk.Button.new_from_icon_name("system-search-symbolic")
        search_button.connect("clicked", self.on_search_triggered)

        filters_button = Gtk.Button.new_from_icon_name("xsi-preferences-symbolic")
        filters_button.connect("clicked", self.on_filters_triggered)

        # Add search input and button to the header bar
        adw_header_bar.pack_start(self.search_entry)
        adw_header_bar.pack_start(search_button)
        adw_header_bar.pack_start(filters_button)

        menu = Gio.Menu.new()
        menu.append("Preferences", "win.preferences")
        menu.append("About", "win.about")

        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        adw_header_bar.pack_end(menu_button)

        # ----------------------------------------------------
        # 2. Setup FlowBox & Container
        # ----------------------------------------------------
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.flowbox = Gtk.FlowBox(
            orientation=Gtk.Orientation.HORIZONTAL,
            row_spacing=12,
            column_spacing=12,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24,
            activate_on_single_click=False,
        )

        self.flowbox.connect("child-activated", self.wallpaper_selected)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)

        #self.page_minus_button = Gtk.Button(icon_name="list-remove-symbolic", width_request=20, margin_bottom=5, margin_end=5, margin_start=5)
        #self.page_counter = Gtk.Entry(text="1", width_request=20, margin_bottom=5, margin_end=5, margin_start=5)
        #self.page_counter.set_width_chars(3)
        #self.page_counter.set_max_width_chars(5)
        #self.page_plus_button = Gtk.Button(icon_name="list-add-symbolic", width_request=20, margin_bottom=5, margin_end=5, margin_start=5)
        adjustment = Gtk.Adjustment(value=0, lower=0, upper=0, step_increment=1)
        self.page_counter = Gtk.SpinButton(adjustment=adjustment, numeric=True, margin_bottom=10, margin_top=10)
        self.page_counter.set_halign(Gtk.Align.CENTER)
        self.page_counter.connect("value-changed", self.on_page_counter_value_changed)

        bottom_box.append(self.page_counter)
        #bottom_box.append(self.page_minus_button)
        #bottom_box.append(self.page_counter)
        #bottom_box.append(self.page_plus_button)

        view = Gtk.ScrolledWindow(child=self.flowbox, vexpand=True)
        main_box.append(view)
        main_box.append(bottom_box)
        adw_toolbar_view.set_content(main_box)

    def show_about_dialog(self):
        about = Adw.AboutDialog.new()
        about.set_application_name("Wallhaven Downloader")
        about.set_version("1.0.0")
        about.set_developer_name("Csani10")
        about.set_website("https://github.com/Csani10/wallhaven-downloader")
        about.set_comments("A GTK4 and libadwaita based application to download wallpapers off of wallhaven.cc, written in python")
        about.set_developers(["Csani10 csanadmozner@gmail.com"])
        about.present(self)

    def load_wallpapers(self, query):
        """Clears existing items and loads new wallpapers for the given query."""
        # Remove old wallpaper tiles from the FlowBox
        self.flowbox.remove_all()

        # Perform the API search
        self.results = self.api.search(query, self.current_filters)

        if not self.results or not self.results.entries:
            adjustment = Gtk.Adjustment(value=0, lower=0, upper=0, step_increment=1)
            self.page_counter.set_adjustment(adjustment)
            print(f"No results found for query: {query}")
            return
        
        adjustment = Gtk.Adjustment(value=self.results.current_page, lower=1, upper=self.results.last_page, step_increment=1)

        self.page_counter.set_adjustment(adjustment)

        for entry in self.results.entries:
            pic = Gtk.Picture.new_for_filename(
                str(entry.download_thumb_small(self.api.thumbs_path))
            )
            pic.set_content_fit(Gtk.ContentFit.CONTAIN)
            pic.set_size_request(300, 200)

            pic.set_halign(Gtk.Align.CENTER)
            pic.set_valign(Gtk.Align.CENTER)
            pic.set_margin_bottom(5)
            pic.set_margin_start(5)
            pic.set_margin_end(5)
            pic.set_margin_top(5)

            pic.id = entry.id

            self.flowbox.append(pic)

    def on_search_triggered(self, widget):
        """Callback for search button click or pressing Enter in search entry."""
        query = self.search_entry.get_text().strip()
        if query:
            self.load_wallpapers(query)

    def on_page_counter_value_changed(self, widget):
        value = self.page_counter.get_value_as_int()
        if value == self.results.current_page:
            return

        query = self.search_entry.get_text().strip()
        self.current_filters.page = value
        if query:
            self.load_wallpapers(query)

    def on_filters_triggered(self, widget):
        dialog = FiltersDialog(current_filters=self.current_filters)
        dialog.connect("applied", self.on_filters_applied)

        dialog.present(self.get_root())

    def on_filters_applied(self, widget, filters):
        self.current_filters = filters

        query = self.search_entry.get_text().strip()
        if query:
            self.load_wallpapers(query)

    def wallpaper_selected(self, flowbox, child):
        picture = child.get_child()

        if hasattr(picture, "id"):
            info_page = WallpaperInfoPage(api=self.api, wallpaper_id=picture.id)
            self.adw_navigation_page.push(page=info_page)

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.config = AppConfig()
        
        # Initialize API using saved config values
        self.api = WallhavenAPI(
            api_key=self.config.api_key,
            download_path=self.config.download_path
        )

        self.set_title("Wallhaven Downloader")
        self.set_default_size(800, 600)

        # Action handlers
        pref_action = Gio.SimpleAction.new("preferences", None)
        pref_action.connect("activate", self._on_preferences_activated)
        self.add_action(pref_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about_activated)
        self.add_action(about_action)

        adw_navigation_view = Adw.NavigationView.new()
        self.main_page = MainPage(adw_navigation_page=adw_navigation_view, api=self.api)
        adw_navigation_view.add(page=self.main_page)

        self.set_content(content=adw_navigation_view)

    def _on_preferences_activated(self, action, parameter):
        dialog = PreferencesDialog(config=self.config)
        dialog.present(self)

    def _on_about_activated(self, action, parameter):
        self.main_page.show_about_dialog()


class WallhavenDownloader(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.csani.wallhaven_downloader")

    def do_activate(self):
        # Present the main window when activated
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()


if __name__ == "__main__":
    app = WallhavenDownloader()
    sys.exit(app.run(sys.argv))
