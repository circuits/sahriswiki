/*
 * Sahris
 *
 * @author      James Mills, prologic at shortcircuit dot net dot au
 * @copyright   (C) 2009, SoftCircuit (James Mills)
 * @date        8th July 2009
 *
 * @license     MIT (See LICENSE file in source distribution)
 */

$.fn.switchClass = function(remove, add) {
    return $(this).removeClass(remove).addClass(add);
}
 
Ext.ns("Sahris");

Sahris = (function() {
    var version = "0.1";

    return {
        init: function() {
            var ui = new Sahris.UI();
            ui.load();
        },
        
        getVersion: function() {
            return version;
        }
    };
})();

Sahris.Menu = Ext.extend(Ext.util.Observable, {
    constructor: function() {
        Sahris.Menu.superclass.constructor.call(this);

        this.addEvents(
            "loaded",
            "failed"
        );

        this.init();
    },

    init: function() {
        if (this.el == null) {
            this.el = $("#menu");
        }
        this.loaded = false;

        this.page = new Sahris.Page("SiteMenu");
        this.parser = new Sahris.Parser();

        this.page.on("loaded", this.onMenuLoaded, this);
        this.page.on("failed", this.onMenuFailed, this);
    },
    
    load: function() {
        this.page.load("SiteMenu");
    },

    onMenuLoaded: function(page) {
        var menu = $("#menu");
        menu.empty();

        this.parser.parse(menu[0], page.text);

        $("#menu a").click(function(e) {
            $("#menu li.first").removeClass("first active");
            $(this).parent().addClass("first active");
            var hash = this.href;
            if (hash && hash[0] == "#") {
                hash = hash.replace(/^.*#/, '');
                $.history.load(hash);
                return false;
            }
        });

        $("#menu li:first").addClass("first active");
    },

    onMenuFailed: function(page) {
    }
});

Sahris.Page = Ext.extend(Ext.util.Observable, {
    constructor: function() {
        Sahris.Page.superclass.constructor.call(this);

        this.addEvents(
            "loaded",
            "failed"
        );

        this.init();
    },

    init: function() {
        this.clear();
    },

    clear: function() {
        this.name = "";
        this.text = "";
        this.rev = 0;
        this.author = "";
        this.comment = "";
    },

    load: function(name) {
        this.clear();
        this.name = name;

        var callback = function(o) {
            this.success = o.success;
            if (o.success) {
                Ext.apply(this, o.page);
                Ext.apply(this, o.meta);
                this.fireEvent("loaded", this);
            } else {
                this.message = o.message;
                this.fireEvent("failed", this);
            }
        }

        $.getJSON("/wiki/" + name, callback.createDelegate(this));
    }
});

Sahris.Parser = Ext.extend(Ext.util.Observable, {
    interwiki: {
        MeatBall: "http://www.usemod.com/cgi-bin/mb.pl?"
    },
    linkFormat: "#",

    constructor: function(config) {
        Ext.apply(this, config);
        Sahris.Parser.superclass.constructor.call(this);

        this.addEvents(
            "parsed"
        );

        this.init();
    },

    init: function() {
        this.creole = new Parse.Simple.Creole(this);
    },
    
    parse: function(el, text) {
        this.creole.parse(el, text);
        this.fireEvent("parsed");
    }
});

Sahris.Template = Ext.extend(Ext.util.Observable, {
    url: null,

    constructor: function(config) {
        Ext.apply(this, config);
        Sahris.Template.superclass.constructor.call(this);

        this.addEvents(
            "loaded",
            "failed"
        );

        this.init();
    },

    init: function() {
    },
    
    load: function() {
        var callback = function() {
            this.fireEvent("loaded", this);
        };

        $("body").load(this.url, callback.createDelegate(this));
    }
});

Sahris.UI = Ext.extend(Ext.util.Observable, {
    menu: new Sahris.Menu(),
    page: new Sahris.Page(),
    parser: new Sahris.Parser(),

    editing: false,
    viewing: false,

    templates: {
        error: $.template("<h1>Error</h1><p class=\"message\">${message}</p>"),
        meta: $.template("<p>Last edited by ${author} (Revision: ${rev}) " +
            "about ${date}</p>")
    },

    constructor: function() {
        Sahris.UI.superclass.constructor.call(this);

        this.addEvents(
            "loaded",
            "failed"
        );

        this.on("loaded", this.onLoaded, this);
        this.on("failed", this.onFailed, this);
        this.page.on("loaded", this.onPageLoaded, this);
        this.page.on("failed", this.onPageFailed, this);

        this.el = $("body");

        this.init();
    },

    init: function() {
        this.loaded = false;
        this.tpl = new Sahris.Template({
            url: "/templates/base.xhtml"
        });
    },
    
    load: function() {
        this.tpl.load();
        this.tpl.on("loaded", function(tpl) {
            this.fireEvent("loaded", tpl);
        }, this);
        this.tpl.on("failed", function(tpl) {
            this.fireEvent("failed", tpl);
        }, this);
    },

    edit: function(flag) {
        if (flag) {
            if (this.editing) return;
            this.viewing = false;
            this.editing = true;

            $("#page").hide();
            $("#editor").show();

            $("#editor #fields input[name=comment]").val("");

            $("#title").html("Editing: " + this.page.name);
            $("#editor textarea").val(this.page.text);

            $("#buttons a#a").text("Save");
            $("#buttons a#b").text("Cancel");
        } else {
            if (this.viewing) return;
            this.viewing = true;
            this.editing = false;
            $("#page").show();
            $("#editor").hide();
            $("#buttons a#a").text("Edit");
            $("#buttons a#b").text("More...");

            if (this.page.name == "SiteMenu") {
                this.menu.load();
            }
            this.displayPage(this.page.name);
        }
    },

    save: function() {
        if (this.viewing) return;

        var data = {
            name: this.page.name,
            text: $("#editor #text textarea").val(),
            comment: $("#editor #fields input[name=comment]").val(),
            author: $("#editor #fields input[name=author]").val()
        };


        var callback = function(o) {
            this.setStatus(o.message);
        };

        $.ajax({
            type: "POST",
            url: "/wiki/" + this.page.name,
            data: $.json.encode(data),
            dataType: "json",
            contentType: "application/javascript",
            success: callback.createDelegate(this)
        });

        this.edit(false);
    },

    displayPage: function(name) {
        console.log("Displaying page " + name);
        this.page.load(name);
        this.pageEl.empty();
    },

    clearError: function() {
        console.log("Clearing error...");
        if ($("#content").attr("class") == "error") {
            $("#content").switchClass("error", "content");
            $("#page").addClass("wiki");
        }
    },

    setError: function(message) {
        if ($("#content").attr("class") == "content") {
            $("#content").switchClass("content", "error");
        }
        this.pageEl.append(this.templates.error, {message: message});
    },

    setStatus: function() {
        var args = arguments;
        $("#status").fadeOut("slow", function() {
            if (args.length == 2) {
                $("#status").empty().append(args[0], args[1]).fadeIn("slow");
            } else {
                $("#status").empty().append(args[0]).fadeIn("slow");
            }
        });
    },

    setTitle: function(title) {
        console.log("Setting title...");
        $("#title").html(title);
    },

    onKeyPressed: function(e) {
        if (e.keyCode == 27) {
            if (this.editing) {
                this.edit(false);
            }
        }
    },

    onButton: function(e) {
        var action = $(e.target).text();
        if (action == "Save") {
            this.save();
        } else if (action == "Cancel") {
            this.edit(false);
        } else if (action == "Edit") {
            this.edit(true);
        } else {
            console.log("Invalid action: " + action);
        }
    },

    onHistory: function(hash) {
        console.log("History changed: " + hash);
        var name = "";
        if (hash) {
            name = hash;
        } else {
            name = "FrontPage";
        }
        this.displayPage(name);
    },

    onLoaded: function(tpl) {
        console.log("UI loaded")
        this.el.html(tpl.text);

        this.pageEl = $("#content > #page");

        this.menu.load();

        $("#editor textarea").markItUp(mySettings);
        $("#editor textarea").width($("#content").width());
        $("#editor textarea").height($("#content").height() * 0.8);

        $.ajax({
            type: "GET",
            url: "/getip",
            dataType: "json",
            success: function(data) {
                $("#editor #fields input[name=author]").val(data);
            }
        });

        $("#metanav a").click(function(e) {
            $("#menu li.first").removeClass("first active");
            var hash = this.href;
            if (hash && hash[0] == "#") {
                hash = hash.replace(/^.*#/, '');
                $.history.load(hash);
                return false;
            }
        });

        $("#ctxnav a").click(function(e) {
            $("#menu li.first").removeClass("first active");
            var hash = this.href;
            if (hash && hash[0] == "#") {
                hash = hash.replace(/^.*#/, '');
                $.history.load(hash);
                return false;
            }
        });

        var buttonCallback = function(e) {
            e.preventDefault();
            this.onButton(e);
        };
        $("#buttons a").click(buttonCallback.createDelegate(this));

        var dblclickCallback = function() {
            this.edit(true);
        };

        $("#content").dblclick(dblclickCallback.createDelegate(this));
        $(document).keypress(this.onKeyPressed);

        var callback = function(hash) {
            this.onHistory(hash);
        };
        $.history.init(callback.createDelegate(this));
    },

    onFailed: function() {
        console.log("UI failed")
    },

    onPageLoaded: function(page) {
        console.log("Page loaded...");
        console.log(page);

        this.parser.parse(this.pageEl[0], page.text);

        $("#content > #page a").click(function(e) {
            $("#menu li.first").removeClass("first active");
            var hash = this.href;
            if (hash && hash[0] == "#") {
                hash = hash.replace(/^.*#/, '');
                $.history.load(hash);
                return false;
            }
        });

        $("#ctxnav a#history").attr("href", "#History/" + name);

        this.setStatus(this.templates.meta, {
                author: page.author,
                rev: page.rev,
                date: prettyDate(page.date * 1000)
        });

        this.viewing = true;
    },

    onPageFailed: function(page) {
        console.log("Page failed...");
        console.log(page);

        this.setError(page.message);
    }
});

Ext.onReady(Sahris.init, Sahris);
