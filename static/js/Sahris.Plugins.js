/*
 * Sahris Plugins
 *
 * @author      James Mills, prologic at shortcircuit dot net dot au
 * @copyright   (C) 2009, SoftCircuit (James Mills)
 * @date        8th July 2009
 *
 * @license     MIT (See LICENSE file in source distribution)
 */

Sahris.Plugins["HelloWorld"] = new Class({
    Implements: Sahris.Plugin,

    run: function (node, data) {
        $(node).set("html", "Hello World!");
    }
});

Sahris.Plugins["html"] = new Class({
    Implements: Sahris.Plugin,

    run: function (node, data) {
        $(node).set("html", data);
    }
});

var PREFERENCES_TPL = "<div id=\"preferences\" class=\"preferences\"><h2>Preferences</h2><div class=\"system-message\" style=\"display: none;\" /><form method=\"post\" action=\"\" id=\"preferencesForm\"><fieldset><legend>Required</legend><div><label>Signature: <input type=\"signature\" name=\"signature\" class=\"textwidget\" size=\"20\" value=\"AnonymousUser\" /></label></div></fieldset><div class=\"buttons\"><input id=\"saveBtn\" type=\"button\" value=\"Save\" /></div></form></div>";

Sahris.Plugins["Preferences"] = new Class({
    Implements: Sahris.Plugin,

    run: function (node, data) {
        $(node).set("html", PREFERENCES_TPL);
    }
});
