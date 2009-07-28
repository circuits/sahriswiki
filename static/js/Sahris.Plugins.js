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

var PREFERENCES_TPL = "<div id=\"preferences\" class=\"preferences\"><h2>User Preferences</h2><div class=\"system-message\" style=\"display: none;\" /><h3>Delete Account</h3><form method=\"post\" action=\"\" id=\"deleteAccountForm\"><div class=\"field\"><label>Password:<input type=\"password\" name=\"password\" class=\"textwidget\" size=\"20\" /></label></div><div class=\"buttons\"><input id=\"deleteBtn\" type=\"button\" value=\"Delete account\" /></div></form><h3>Change Password</h3><form method=\"post\" action=\"\" id=\"changePasswordForm\"><div class=\"field\"><label>Old Password:<input type=\"password\" name=\"oldPassword\" class=\"textwidget\" size=\"20\" /></label></div><div class=\"field\"><label>New Password:<input type=\"password\" name=\"newPassword\" class=\"textwidget\" size=\"20\" /></label></div><div class=\"field\"><label>Confirm Password:<input type=\"password\" name=\"newPasswordConfirm\" class=\"textwidget\" size=\"20\" /></label></div><div class=\"buttons\"><input id=\"changeBtn\" type=\"button\" value=\"Change password\" /></div></form></div>";

Sahris.Plugins["Preferences"] = new Class({
    Implements: Sahris.Plugin,

    run: function (node, data) {
        $(node).set("html", PREFERENCES_TPL);
    }
});
