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

var REGISTER_TPL = "<div class=\"register\" id=\"register\"><h2>Register an account</h2><div class=\"system-message\" style=\"display: none;\" /><form action=\"\" id=\"registerForm\" method=\"post\"><div></div><fieldset><legend>Required</legend><div><label>Username:<input type=\"text\" size=\"20\" class=\"textwidget\" name=\"user\"/></label></div><div><label>Password:<input type=\"password\" size=\"20\" class=\"textwidget\" name=\"password\"/></label></div><div><label>Confirm Password:<input type=\"password\" size=\"20\" class=\"textwidget\" name=\"passwordConfirm\"/></label></div></fieldset><fieldset><legend>Optional</legend><div><label>Name:<input type=\"text\" size=\"20\" class=\"textwidget\" name=\"name\"/></label></div><div><label>Email:<input type=\"text\" size=\"20\" class=\"textwidget\" name=\"email\"/></label><p>Entering your email address willenable you to reset your password if you ever forget it.</p></div></fieldset><input id=\"create\" type=\"button\" value=\"Create account\"/></form></div>";

Sahris.Plugins["Register"] = new Class({
    Implements: Sahris.Plugin,

    run: function (node, data) {
        $(node).set("html", REGISTER_TPL);
    }
});

var LOGIN_TPL = "<div id=\"login\" class=\"login\"><h2>Login</h2><div class=\"system-message\" style=\"display: none;\" /><form method=\"post\" id=\"loginForm\" action=\"\"><div><label for=\"username\">Username:</label><input type=\"text\" id=\"username\" name=\"username\" class=\"textwidget\" size=\"20\" /></div><div><label for=\"password\">Password:</label><input type=\"password\" id=\"password\" name=\"password\" class=\"textwidget\" size=\"20\" /></div><input id=\"loginBtn\" type=\"button\" value=\"Login\" /><p><a href=\"\">Forgot your password?</a></p></form></div>";

Sahris.Plugins["Login"] = new Class({
    Implements: Sahris.Plugin,

    run: function (node, data) {
        $(node).set("html", LOGIN_TPL);
    }
});

PREFERENCES_TPL = "<div id=\"preferences\" class=\"preferences\"><h2>User Preferences</h2><div class=\"system-message\" style=\"display: none;\" /><h3>Delete Account</h3><form method=\"post\" action=\"\" id=\"deleteAccountForm\"><div class=\"field\"><label>Password:<input type=\"password\" name=\"password\" class=\"textwidget\" size=\"20\" /></label></div><div class=\"buttons\"><input id=\"deleteBtn\" type=\"button\" value=\"Delete account\" /></div></form><h3>Change Password</h3><form method=\"post\" action=\"\" id=\"changePasswordForm\"><div class=\"field\"><label>Old Password:<input type=\"password\" name=\"oldPassword\" class=\"textwidget\" size=\"20\" /></label></div><div class=\"field\"><label>New Password:<input type=\"password\" name=\"newPassword\" class=\"textwidget\" size=\"20\" /></label></div><div class=\"field\"><label>Confirm Password:<input type=\"password\" name=\"newPasswordConfirm\" class=\"textwidget\" size=\"20\" /></label></div><div class=\"buttons\"><input id=\"changeBtn\" type=\"button\" value=\"Change password\" /></div></form></div>";

Sahris.Plugins["Preferences"] = new Class({
    Implements: Sahris.Plugin,

    run: function (node, data) {
        $(node).set("html", PREFERENCES_TPL);
    }
});
