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

var PREFERENCES_TPL = "<div id=\"preferences\" class=\"preferences\"><h2>Preferences</h2><div class=\"system-message\" style=\"display: none;\" /><form id=\"preferencesForm\" name=\"preferencesForm\" action=\"\" method=\"post\"><fieldset><legend>Required</legend><div><label>Signature: <input type=\"text\" name=\"signature\" class=\"textwidget\" size=\"20\" /></label></div></fieldset><div class=\"buttons\"><input id=\"saveBtn\" type=\"button\" value=\"Save\" /></div></form></div>";

Sahris.Plugins["Preferences"] = new Class({
    Implements: Sahris.Plugin,

    el: null,

    save: function() {
        var uri = new URI(location.href);
        Cookie.write("signature",
            this.el.getElement("[name=signature]").get("value"), {
            domain: uri.parsed.host,
            duration: 90
        });
        this.setMessage(this.el, "Preferences saved");
    },

    run: function (node, data) {
        this.el = $(node);
        this.el.set("html", PREFERENCES_TPL);

        this.el.getElement("[name=signature]").set("value",
            Cookie.read("signature") || "");

        this.el.getElement("#preferencesForm").on("submit", function (e) {
            e.preventDefault();
            this.save();
        }.bind(this));

        this.el.getElement("#saveBtn").on("click", function (e) {
            e.preventDefault();
            this.save();
        }.bind(this));
    }
});
