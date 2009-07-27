/*
 * Creole Wiki Parser
 *
 */

var Creole = {};

Creole.Rules = new Class({
    // For the inline elements:
    proto: new RegExp("http|https|ftp|nntp|news|mailto|telnet|file|irc"),
    link: new RegExp("(\\[\\[(.+?) \s*([|] \s* (.+?) \s*)?]])"),
    image: new RegExp("({{(.+?) \s*([|] \s* (.+?) \s*)?}})"),
    macro: new RegExp("(<<( \w+)(\( ( .*?) \))? \s*([|] \s* ( .+?) \s* )?>>)"),
    code: new RegExp("( {{{ (.*?) }}} )"),
    emph: new RegExp("( (?!:)// )"), // there must be no : in front of the //
                          // avoids italic rendering in urls with
                          // unknown protocols
    strong: new RegExp(" \\\\*\\\\* "),
    linebreak: new RegExp(" \\\\\\\\ "),
    escape: new RegExp("( ~ (\S) )"),
    char: new RegExp("( . )"),

    // For the block elements:
    separator: new RegExp("( ^ \s* ---- \s* $ )"), // horizontal line
    line: new RegExp("( ^ \s* $ )"), // empty line that separates paragraphs
    head: new RegExp("((=+) \s*( .*? ) \s*(=*) \s*$)"),
    text: new RegExp("( .+ )"),

    // Matches the whole list, separate items are parsed later. The
    // list *must* start with a single bullet.
    list: new RegExp("(^ [ \t]* ([*][^*\#]|[\#][^\#*]).* $( \n[ \t]* [*\#]+.* $ )*)"),

    item: new RegExp("(^ \s*( [\#*]+) \s*( .*?)$)"), // Matches single list items
    pre: new RegExp("(^{{{ \s* $(\n)?(([\#]!(\w*?)(\s+.*)?$)?(.|\n)+?)(\n)?^}}} \s*$)"),
    pre_escape: new RegExp(" ^(\s*) ~ ( \}\}\} \s*) $"),
    table: new RegExp("(^ \s*[|].*? \s*[|]? \s*$)"),

    initialize: function () {
        // For the inline elements:
        this.url =  new RegExp("((^ | (?=\s | [.,:;!?()/=]))(~)?( ( / " + this.proto + " / ):\S+? )($ | (?=\s | [,.:;!?()] (\s | $))))");

        // For splitting table cells:
        this.cell = new RegExp("\| \s*(( [=][^|]+ ) |( ( " + [this.link, this.macro, this.image, this.code].join("|") + " | [^|])+ )) \s*");
    }
});

Creole.rules = new Creole.Rules();

Creole.Parser = new Class({
    Extends: Events,
    Implements: Options,

    rules: Creole.rules,

    options: {},

    initialize: function (options) {
        this.setOptions(options);

        this.raw = null;
        this.root = null;
        this.cur = this.root; // The most recent document node
        this.text = null;     // The node to add inline characters to

        // For pre escaping, in creole 1.0 done with ~:
        //pre_escape_re = re.compile(Rules.pre_escape, re.M | re.X)
        //link_re = re.compile('|'.join([Rules.image, Rules.linebreak, Rules.char]), re.X | re.U) # for link descriptions
        //item_re = re.compile(Rules.item, re.X | re.U | re.M) # for list items
        //cell_re = re.compile(Rules.cell, re.X | re.U) # for table cells

        // For block elements:
        this.block_re = new RegExp([this.rules.line, this.rules.head, this.rules.separator, this.rules.pre, this.rules.list, this.rules.table, this.rules.text].join("|"), "m");

        // For inline elements:
        /*
        inline_re = re.compile('|'.join([Rules.link, Rules.url, Rules.macro,
            Rules.code, Rules.image, Rules.strong, Rules.emph, Rules.linebreak,
            Rules.escape, Rules.char]), re.X | re.U)
        */
    },

    /*
    def _upto(self, node, kinds):
        """
        Look up the tree to the first occurence
        of one of the listed kinds of nodes or root.
        Start at the node node.
        """
        while node.parent is not None and not node.kind in kinds:
            node = node.parent
        return node

    # The _*_repl methods called for matches in regexps. Sometimes the
    # same method needs several names, because of group names in regexps.

    def _url_repl(self, groups):
        """Handle raw urls in text."""

        if not groups.get('escaped_url'):
            # this url is NOT escaped
            target = groups.get('url_target', '')
            node = DocNode('link', self.cur)
            node.content = target
            DocNode('text', node, node.content)
            self.text = None
        else:
            # this url is escaped, we render it as text
            if self.text is None:
                self.text = DocNode('text', self.cur, u'')
            self.text.content += groups.get('url_target')
    _url_target_repl = _url_repl
    _url_proto_repl = _url_repl
    _escaped_url = _url_repl

    def _link_repl(self, groups):
        """Handle all kinds of links."""

        target = groups.get('link_target', '')
        text = (groups.get('link_text', '') or '').strip()
        parent = self.cur
        self.cur = DocNode('link', self.cur)
        self.cur.content = target
        self.text = None
        re.sub(self.link_re, self._replace, text)
        self.cur = parent
        self.text = None
    _link_target_repl = _link_repl
    _link_text_repl = _link_repl

    def _macro_repl(self, groups):
        """Handles macros using the placeholder syntax."""

        name = groups.get('macro_name', '')
        text = (groups.get('macro_text', '') or '').strip()
        node = DocNode('macro', self.cur, name)
        node.args = groups.get('macro_args', '') or ''
        DocNode('text', node, text or name)
        self.text = None
    _macro_name_repl = _macro_repl
    _macro_args_repl = _macro_repl
    _macro_text_repl = _macro_repl

    def _image_repl(self, groups):
        """Handles images and attachemnts included in the page."""

        target = groups.get('image_target', '').strip()
        text = (groups.get('image_text', '') or '').strip()
        node = DocNode("image", self.cur, target)
        DocNode('text', node, text or node.content)
        self.text = None
    _image_target_repl = _image_repl
    _image_text_repl = _image_repl

    def _separator_repl(self, groups):
        self.cur = self._upto(self.cur, ('document', 'section', 'blockquote'))
        DocNode('separator', self.cur)

    def _item_repl(self, groups):
        bullet = groups.get('item_head', u'')
        text = groups.get('item_text', u'')
        if bullet[-1] == '#':
            kind = 'number_list'
        else:
            kind = 'bullet_list'
        level = len(bullet)
        lst = self.cur
        # Find a list of the same kind and level up the tree
        while (lst and
                   not (lst.kind in ('number_list', 'bullet_list') and
                        lst.level == level) and
                    not lst.kind in ('document', 'section', 'blockquote')):
            lst = lst.parent
        if lst and lst.kind == kind:
            self.cur = lst
        else:
            # Create a new level of list
            self.cur = self._upto(self.cur,
                ('list_item', 'document', 'section', 'blockquote'))
            self.cur = DocNode(kind, self.cur)
            self.cur.level = level
        self.cur = DocNode('list_item', self.cur)
        self.parse_inline(text)
        self.text = None
    _item_text_repl = _item_repl
    _item_head_repl = _item_repl

    def _list_repl(self, groups):
        text = groups.get('list', u'')
        self.item_re.sub(self._replace, text)

    def _head_repl(self, groups):
        self.cur = self._upto(self.cur, ('document', 'section', 'blockquote'))
        node = DocNode('header', self.cur, groups.get('head_text', '').strip())
        node.level = len(groups.get('head_head', ' '))
    _head_head_repl = _head_repl
    _head_text_repl = _head_repl

    def _text_repl(self, groups):
        text = groups.get('text', '')
        if self.cur.kind in ('table', 'table_row', 'bullet_list',
            'number_list'):
            self.cur = self._upto(self.cur,
                ('document', 'section', 'blockquote'))
        if self.cur.kind in ('document', 'section', 'blockquote'):
            self.cur = DocNode('paragraph', self.cur)
        else:
            text = u' ' + text
        self.parse_inline(text)
        if groups.get('break') and self.cur.kind in ('paragraph',
            'emphasis', 'strong', 'code'):
            DocNode('break', self.cur, '')
        self.text = None
    _break_repl = _text_repl

    def _table_repl(self, groups):
        row = groups.get('table', '|').strip()
        self.cur = self._upto(self.cur, (
            'table', 'document', 'section', 'blockquote'))
        if self.cur.kind != 'table':
            self.cur = DocNode('table', self.cur)
        tb = self.cur
        tr = DocNode('table_row', tb)

        text = ''
        for m in self.cell_re.finditer(row):
            cell = m.group('cell')
            if cell:
                self.cur = DocNode('table_cell', tr)
                self.text = None
                self.parse_inline(cell)
            else:
                cell = m.group('head')
                self.cur = DocNode('table_head', tr)
                self.text = DocNode('text', self.cur, u'')
                self.text.content = cell.strip('=')
        self.cur = tb
        self.text = None

    def _pre_repl(self, groups):
        self.cur = self._upto(self.cur, ('document', 'section', 'blockquote'))
        kind = groups.get('pre_kind', None)
        text = groups.get('pre_text', u'')
        def remove_tilde(m):
            return m.group('indent') + m.group('rest')
        text = self.pre_escape_re.sub(remove_tilde, text)
        node = DocNode('preformatted', self.cur, text)
        node.sect = kind or ''
        self.text = None
    _pre_text_repl = _pre_repl
    _pre_head_repl = _pre_repl
    _pre_kind_repl = _pre_repl

    def _line_repl(self, groups):
        self.cur = self._upto(self.cur, ('document', 'section', 'blockquote'))

    def _code_repl(self, groups):
        DocNode('code', self.cur, groups.get('code_text', u'').strip())
        self.text = None
    _code_text_repl = _code_repl
    _code_head_repl = _code_repl

    def _emph_repl(self, groups):
        if self.cur.kind != 'emphasis':
            self.cur = DocNode('emphasis', self.cur)
        else:
            self.cur = self._upto(self.cur, ('emphasis', )).parent
        self.text = None

    def _strong_repl(self, groups):
        if self.cur.kind != 'strong':
            self.cur = DocNode('strong', self.cur)
        else:
            self.cur = self._upto(self.cur, ('strong', )).parent
        self.text = None

    def _break_repl(self, groups):
        DocNode('break', self.cur, None)
        self.text = None

    def _escape_repl(self, groups):
        if self.text is None:
            self.text = DocNode('text', self.cur, u'')
        self.text.content += groups.get('escaped_char', u'')

    def _char_repl(self, groups):
        if self.text is None:
            self.text = DocNode('text', self.cur, u'')
        self.text.content += groups.get('char', u'')

    def _replace(self, match):
        """Invoke appropriate _*_repl method. Called for every matched group."""

        groups = match.groupdict()
        for name, text in groups.iteritems():
            if text is not None:
                replace = getattr(self, '_%s_repl' % name)
                replace(groups)
                return

    def parse_inline(self, raw):
        """Recognize inline elements inside blocks."""

        re.sub(self.inline_re, self._replace, raw)
    */

    parse_block: function (raw) {
        var match = this.block_re.search(raw);
        console.log(match);
    },

    parse: function(raw, root) {
        this.raw = raw;
        this.root = root;
        this.parse_block(this.raw);
        return this.root;
});

Creole.parser = new Creole.Parser();
