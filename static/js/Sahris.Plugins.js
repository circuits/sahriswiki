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
    Implements: Plugin,

    run: function (node, data) {
        $(node).set("html", "Hello World!");
    }
});

Sahris.Plugins["html"] = new Class({
    Implements: Plugin,

    run: function (node, data) {
        $(node).set("html", data);
    }
});
