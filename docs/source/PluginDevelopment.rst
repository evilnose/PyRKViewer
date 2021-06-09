=================================================
Plugin Development
=================================================

----------------
Writing plugins
----------------

Here are the steps for writing a plugin:

1. First decide if you want a CommandPlugin or a WindowedPlugin. CommandPlugins are those with one single action and don’t require a dialog display. WindowedPlugin allows for a more complex UI by spawning a window.
2. Create a Python script with a single class that inherits from either CommandPlugin or WindowedPlugin.
3. In the plugin class, create a `PluginMetadata` object named `metadata`. This holds necessary information (e.g. name, author, description) about the plugin. See the sample plugin for an example.
4. If needed, create a constructor that also calls the “super” constructor.
5. Override the inherited methods:
 
 a. If you inherited a CommandPlugin, simply override the “run()”method, which is called when the user clicks on the plugin item
 b. For WindowedPlugin, you need to override “create_window(dialog)”, which passes you the parent dialog in which you can create your widgets.

6. Also keep in mind the event handlers which are called when events occur (e.g. on node created, deleted, etc.). See the same file on plugins for info on these.
