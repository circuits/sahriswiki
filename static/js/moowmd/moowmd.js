//
// showdown.js -- A javascript port of Markdown.
//
// Copyright (c) 2007 John Fraser.
//
// Original Markdown Copyright (c) 2004-2005 John Gruber
//   <http://daringfireball.net/projects/markdown/>
//
// The full source distribution is at:
//
//				A A L
//				T C A
//				T K B
//
//   <http://www.attacklab.net/>
//

//
// Wherever possible, Showdown is a straight, line-by-line port
// of the Perl version of Markdown.
//
// This is not a normal parser design; it's basically just a
// series of string substitutions.  It's hard to read and
// maintain this way,  but keeping Showdown close to the original
// design makes it easier to port new features.
//
// More importantly, Showdown behaves like markdown.pl in most
// edge cases.  So web applications can do client-side preview
// in Javascript, and then build identical HTML on the server.
//
// This port needs the new RegExp functionality of ECMA 262,
// 3rd Edition (i.e. Javascript 1.5).  Most modern web browsers
// should do fine.  Even with the new regular expression features,
// We do a lot of work to emulate Perl's regex functionality.
// The tricky changes in this file mostly have the "attacklab:"
// label.  Major or self-explanatory changes don't.
//
// Smart diff tools like Araxis Merge will be able to match up
// this file with markdown.pl in a useful way.  A little tweaking
// helps: in a copy of markdown.pl, replace "#" with "//" and
// replace "$text" with "text".  Be sure to ignore whitespace
// and line endings.
//


//
// Showdown usage:
//
//   var text = "Markdown *rocks*.";
//
//   var converter = new Attacklab.showdown.converter();
//   var html = converter.makeHtml(text);
//
//   alert(html);
//
// Note: move the sample code to the bottom of this
// file before uncommenting it.
//


//
// Attacklab namespace
//
var Attacklab = Attacklab || {}

//
// Showdown namespace
//
Attacklab.showdown = Attacklab.showdown || {}

//
// converter
//
// Wraps all "globals" so that the only thing
// exposed is makeHtml().
//
Attacklab.showdown.converter = function() {

//
// Globals:
//

// Global hashes, used by various utility routines
var g_urls;
var g_titles;
var g_html_blocks;

// Used to track when we're inside an ordered or unordered list
// (see _ProcessListItems() for details):
var g_list_level = 0;


this.makeHtml = function(text) {
//
// Main function. The order in which other subs are called here is
// essential. Link and image substitutions need to happen before
// _EscapeSpecialCharsWithinTagAttributes(), so that any *'s or _'s in the <a>
// and <img> tags get encoded.
//

	// Clear the global hashes. If we don't clear these, you get conflicts
	// from other articles when generating a page which contains more than
	// one article (e.g. an index page that shows the N most recent
	// articles):
	g_urls = new Array();
	g_titles = new Array();
	g_html_blocks = new Array();

	// attacklab: Replace ~ with ~T
	// This lets us use tilde as an escape char to avoid md5 hashes
	// The choice of character is arbitray; anything that isn't
    // magic in Markdown will work.
	text = text.replace(/~/g,"~T");

	// attacklab: Replace $ with ~D
	// RegExp interprets $ as a special character
	// when it's in a replacement string
	text = text.replace(/\$/g,"~D");

	// Standardize line endings
	text = text.replace(/\r\n/g,"\n"); // DOS to Unix
	text = text.replace(/\r/g,"\n"); // Mac to Unix

	// Make sure text begins and ends with a couple of newlines:
	text = "\n\n" + text + "\n\n";

	// Convert all tabs to spaces.
	text = _Detab(text);

	// Strip any lines consisting only of spaces and tabs.
	// This makes subsequent regexen easier to write, because we can
	// match consecutive blank lines with /\n+/ instead of something
	// contorted like /[ \t]*\n+/ .
	text = text.replace(/^[ \t]+$/mg,"");

	// Turn block-level HTML blocks into hash entries
	text = _HashHTMLBlocks(text);

	// Strip link definitions, store in hashes.
	text = _StripLinkDefinitions(text);

	text = _RunBlockGamut(text);

	text = _UnescapeSpecialChars(text);

	// attacklab: Restore dollar signs
	text = text.replace(/~D/g,"$$");

	// attacklab: Restore tildes
	text = text.replace(/~T/g,"~");

	return text;
}

var _StripLinkDefinitions = function(text) {
//
// Strips link definitions from text, stores the URLs and titles in
// hash references.
//

	// Link defs are in the form: ^[id]: url "optional title"

	/*
		var text = text.replace(/
				^[ ]{0,3}\[(.+)\]:  // id = $1  attacklab: g_tab_width - 1
				  [ \t]*
				  \n?				// maybe *one* newline
				  [ \t]*
				<?(\S+?)>?			// url = $2
				  [ \t]*
				  \n?				// maybe one newline
				  [ \t]*
				(?:
				  (\n*)				// any lines skipped = $3 attacklab: lookbehind removed
				  ["(]
				  (.+?)				// title = $4
				  [")]
				  [ \t]*
				)?					// title is optional
				(?:\n+|$)
			  /gm,
			  function(){...});
	*/
	var text = text.replace(/^[ ]{0,3}\[(.+)\]:[ \t]*\n?[ \t]*<?(\S+?)>?[ \t]*\n?[ \t]*(?:(\n*)["(](.+?)[")][ \t]*)?(?:\n+)/gm,
		function (wholeMatch,m1,m2,m3,m4) {
			m1 = m1.toLowerCase();
			g_urls[m1] = _EncodeAmpsAndAngles(m2);  // Link IDs are case-insensitive
			if (m3) {
				// Oops, found blank lines, so it's not a title.
				// Put back the parenthetical statement we stole.
				return m3+m4;
			} else if (m4) {
				g_titles[m1] = m4.replace(/"/g,"&quot;");
			}
			
			// Completely remove the definition from the text
			return "";
		}
	);

	return text;
}

var _HashHTMLBlocks = function(text) {
	// attacklab: Double up blank lines to reduce lookaround
	text = text.replace(/\n/g,"\n\n");

	// Hashify HTML blocks:
	// We only want to do this for block-level HTML tags, such as headers,
	// lists, and tables. That's because we still want to wrap <p>s around
	// "paragraphs" that are wrapped in non-block-level tags, such as anchors,
	// phrase emphasis, and spans. The list of tags we're looking for is
	// hard-coded:
	var block_tags_a = "p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math|ins|del"
	var block_tags_b = "p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math"

	// First, look for nested blocks, e.g.:
	//   <div>
	//     <div>
	//     tags for inner block must be indented.
	//     </div>
	//   </div>
	//
	// The outermost tags must start at the left margin for this to match, and
	// the inner nested divs must be indented.
	// We need to do this before the next, more liberal match, because the next
	// match will start at the first `<div>` and stop at the first `</div>`.

	// attacklab: This regex can be expensive when it fails.
	/*
		var text = text.replace(/
		(						// save in $1
			^					// start of line  (with /m)
			<($block_tags_a)	// start tag = $2
			\b					// word break
								// attacklab: hack around khtml/pcre bug...
			[^\r]*?\n			// any number of lines, minimally matching
			</\2>				// the matching end tag
			[ \t]*				// trailing spaces/tabs
			(?=\n+)				// followed by a newline
		)						// attacklab: there are sentinel newlines at end of document
		/gm,function(){...}};
	*/
	text = text.replace(/^(<(p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math|ins|del)\b[^\r]*?\n<\/\2>[ \t]*(?=\n+))/gm,hashElement);

	//
	// Now match more liberally, simply from `\n<tag>` to `</tag>\n`
	//

	/*
		var text = text.replace(/
		(						// save in $1
			^					// start of line  (with /m)
			<($block_tags_b)	// start tag = $2
			\b					// word break
								// attacklab: hack around khtml/pcre bug...
			[^\r]*?				// any number of lines, minimally matching
			.*</\2>				// the matching end tag
			[ \t]*				// trailing spaces/tabs
			(?=\n+)				// followed by a newline
		)						// attacklab: there are sentinel newlines at end of document
		/gm,function(){...}};
	*/
	text = text.replace(/^(<(p|div|h[1-6]|blockquote|pre|table|dl|ol|ul|script|noscript|form|fieldset|iframe|math)\b[^\r]*?.*<\/\2>[ \t]*(?=\n+)\n)/gm,hashElement);

	// Special case just for <hr />. It was easier to make a special case than
	// to make the other regex more complicated.  

	/*
		text = text.replace(/
		(						// save in $1
			\n\n				// Starting after a blank line
			[ ]{0,3}
			(<(hr)				// start tag = $2
			\b					// word break
			([^<>])*?			// 
			\/?>)				// the matching end tag
			[ \t]*
			(?=\n{2,})			// followed by a blank line
		)
		/g,hashElement);
	*/
	text = text.replace(/(\n[ ]{0,3}(<(hr)\b([^<>])*?\/?>)[ \t]*(?=\n{2,}))/g,hashElement);

	// Special case for standalone HTML comments:

	/*
		text = text.replace(/
		(						// save in $1
			\n\n				// Starting after a blank line
			[ ]{0,3}			// attacklab: g_tab_width - 1
			<!
			(--[^\r]*?--\s*)+
			>
			[ \t]*
			(?=\n{2,})			// followed by a blank line
		)
		/g,hashElement);
	*/
	text = text.replace(/(\n\n[ ]{0,3}<!(--[^\r]*?--\s*)+>[ \t]*(?=\n{2,}))/g,hashElement);

	// PHP and ASP-style processor instructions (<?...?> and <%...%>)

	/*
		text = text.replace(/
		(?:
			\n\n				// Starting after a blank line
		)
		(						// save in $1
			[ ]{0,3}			// attacklab: g_tab_width - 1
			(?:
				<([?%])			// $2
				[^\r]*?
				\2>
			)
			[ \t]*
			(?=\n{2,})			// followed by a blank line
		)
		/g,hashElement);
	*/
	text = text.replace(/(?:\n\n)([ ]{0,3}(?:<([?%])[^\r]*?\2>)[ \t]*(?=\n{2,}))/g,hashElement);

	// attacklab: Undo double lines (see comment at top of this function)
	text = text.replace(/\n\n/g,"\n");
	return text;
}

var hashElement = function(wholeMatch,m1) {
	var blockText = m1;

	// Undo double lines
	blockText = blockText.replace(/\n\n/g,"\n");
	blockText = blockText.replace(/^\n/,"");
	
	// strip trailing blank lines
	blockText = blockText.replace(/\n+$/g,"");
	
	// Replace the element text with a marker ("~KxK" where x is its key)
	blockText = "\n\n~K" + (g_html_blocks.push(blockText)-1) + "K\n\n";
	
	return blockText;
};

var _RunBlockGamut = function(text) {
//
// These are all the transformations that form block-level
// tags like paragraphs, headers, and list items.
//
	text = _DoHeaders(text);

	// Do Horizontal Rules:
	var key = hashBlock("<hr />");
	text = text.replace(/^[ ]{0,2}([ ]?\*[ ]?){3,}[ \t]*$/gm,key);
	text = text.replace(/^[ ]{0,2}([ ]?-[ ]?){3,}[ \t]*$/gm,key);
	text = text.replace(/^[ ]{0,2}([ ]?_[ ]?){3,}[ \t]*$/gm,key);

	text = _DoLists(text);
	text = _DoCodeBlocks(text);
	text = _DoBlockQuotes(text);

	// We already ran _HashHTMLBlocks() before, in Markdown(), but that
	// was to escape raw HTML in the original Markdown source. This time,
	// we're escaping the markup we've just created, so that we don't wrap
	// <p> tags around block-level tags.
	text = _HashHTMLBlocks(text);
	text = _FormParagraphs(text);

	return text;
}


var _RunSpanGamut = function(text) {
//
// These are all the transformations that occur *within* block-level
// tags like paragraphs, headers, and list items.
//

	text = _DoCodeSpans(text);
	text = _EscapeSpecialCharsWithinTagAttributes(text);
	text = _EncodeBackslashEscapes(text);

	// Process anchor and image tags. Images must come first,
	// because ![foo][f] looks like an anchor.
	text = _DoImages(text);
	text = _DoAnchors(text);

	// Make links out of things like `<http://example.com/>`
	// Must come after _DoAnchors(), because you can use < and >
	// delimiters in inline links like [this](<url>).
	text = _DoAutoLinks(text);
	text = _EncodeAmpsAndAngles(text);
	text = _DoItalicsAndBold(text);

	// Do hard breaks:
	text = text.replace(/  +\n/g," <br />\n");

	return text;
}

var _EscapeSpecialCharsWithinTagAttributes = function(text) {
//
// Within tags -- meaning between < and > -- encode [\ ` * _] so they
// don't conflict with their use in Markdown for code, italics and strong.
//

	// Build a regex to find HTML tags and comments.  See Friedl's 
	// "Mastering Regular Expressions", 2nd Ed., pp. 200-201.
	var regex = /(<[a-z\/!$]("[^"]*"|'[^']*'|[^'">])*>|<!(--.*?--\s*)+>)/gi;

	text = text.replace(regex, function(wholeMatch) {
		var tag = wholeMatch.replace(/(.)<\/?code>(?=.)/g,"$1`");
		tag = escapeCharacters(tag,"\\`*_");
		return tag;
	});

	return text;
}

var _DoAnchors = function(text) {
//
// Turn Markdown link shortcuts into XHTML <a> tags.
//
	//
	// First, handle reference-style links: [link text] [id]
	//

	/*
		text = text.replace(/
		(							// wrap whole match in $1
			\[
			(
				(?:
					\[[^\]]*\]		// allow brackets nested one level
					|
					[^\[]			// or anything else
				)*
			)
			\]

			[ ]?					// one optional space
			(?:\n[ ]*)?				// one optional newline followed by spaces

			\[
			(.*?)					// id = $3
			\]
		)()()()()					// pad remaining backreferences
		/g,_DoAnchors_callback);
	*/
	text = text.replace(/(\[((?:\[[^\]]*\]|[^\[\]])*)\][ ]?(?:\n[ ]*)?\[(.*?)\])()()()()/g,writeAnchorTag);

	//
	// Next, inline-style links: [link text](url "optional title")
	//

	/*
		text = text.replace(/
			(						// wrap whole match in $1
				\[
				(
					(?:
						\[[^\]]*\]	// allow brackets nested one level
					|
					[^\[\]]			// or anything else
				)
			)
			\]
			\(						// literal paren
			[ \t]*
			()						// no id, so leave $3 empty
			<?(.*?)>?				// href = $4
			[ \t]*
			(						// $5
				(['"])				// quote char = $6
				(.*?)				// Title = $7
				\6					// matching quote
				[ \t]*				// ignore any spaces/tabs between closing quote and )
			)?						// title is optional
			\)
		)
		/g,writeAnchorTag);
	*/
	text = text.replace(/(\[((?:\[[^\]]*\]|[^\[\]])*)\]\([ \t]*()<?(.*?)>?[ \t]*((['"])(.*?)\6[ \t]*)?\))/g,writeAnchorTag);

	//
	// Last, handle reference-style shortcuts: [link text]
	// These must come last in case you've also got [link test][1]
	// or [link test](/foo)
	//

	/*
		text = text.replace(/
		(		 					// wrap whole match in $1
			\[
			([^\[\]]+)				// link text = $2; can't contain '[' or ']'
			\]
		)()()()()()					// pad rest of backreferences
		/g, writeAnchorTag);
	*/
	text = text.replace(/(\[([^\[\]]+)\])()()()()()/g, writeAnchorTag);

	return text;
}

var writeAnchorTag = function(wholeMatch,m1,m2,m3,m4,m5,m6,m7) {
	if (m7 == undefined) m7 = "";
	var whole_match = m1;
	var link_text   = m2;
	var link_id	 = m3.toLowerCase();
	var url		= m4;
	var title	= m7;
	
	if (url == "") {
		if (link_id == "") {
			// lower-case and turn embedded newlines into spaces
			link_id = link_text.toLowerCase().replace(/ ?\n/g," ");
		}
		url = "#"+link_id;
		
		if (g_urls[link_id] != undefined) {
			url = g_urls[link_id];
			if (g_titles[link_id] != undefined) {
				title = g_titles[link_id];
			}
		}
		else {
			if (whole_match.search(/\(\s*\)$/m)>-1) {
				// Special case for explicit empty url
				url = "";
			} else {
				return whole_match;
			}
		}
	}	
	
	url = escapeCharacters(url,"*_");
	var result = "<a href=\"" + url + "\"";
	
	if (title != "") {
		title = title.replace(/"/g,"&quot;");
		title = escapeCharacters(title,"*_");
		result +=  " title=\"" + title + "\"";
	}
	
	result += ">" + link_text + "</a>";
	
	return result;
}


var _DoImages = function(text) {
//
// Turn Markdown image shortcuts into <img> tags.
//

	//
	// First, handle reference-style labeled images: ![alt text][id]
	//

	/*
		text = text.replace(/
		(						// wrap whole match in $1
			!\[
			(.*?)				// alt text = $2
			\]

			[ ]?				// one optional space
			(?:\n[ ]*)?			// one optional newline followed by spaces

			\[
			(.*?)				// id = $3
			\]
		)()()()()				// pad rest of backreferences
		/g,writeImageTag);
	*/
	text = text.replace(/(!\[(.*?)\][ ]?(?:\n[ ]*)?\[(.*?)\])()()()()/g,writeImageTag);

	//
	// Next, handle inline images:  ![alt text](url "optional title")
	// Don't forget: encode * and _

	/*
		text = text.replace(/
		(						// wrap whole match in $1
			!\[
			(.*?)				// alt text = $2
			\]
			\s?					// One optional whitespace character
			\(					// literal paren
			[ \t]*
			()					// no id, so leave $3 empty
			<?(\S+?)>?			// src url = $4
			[ \t]*
			(					// $5
				(['"])			// quote char = $6
				(.*?)			// title = $7
				\6				// matching quote
				[ \t]*
			)?					// title is optional
		\)
		)
		/g,writeImageTag);
	*/
	text = text.replace(/(!\[(.*?)\]\s?\([ \t]*()<?(\S+?)>?[ \t]*((['"])(.*?)\6[ \t]*)?\))/g,writeImageTag);

	return text;
}

var writeImageTag = function(wholeMatch,m1,m2,m3,m4,m5,m6,m7) {
	var whole_match = m1;
	var alt_text   = m2;
	var link_id	 = m3.toLowerCase();
	var url		= m4;
	var title	= m7;

	if (!title) title = "";
	
	if (url == "") {
		if (link_id == "") {
			// lower-case and turn embedded newlines into spaces
			link_id = alt_text.toLowerCase().replace(/ ?\n/g," ");
		}
		url = "#"+link_id;
		
		if (g_urls[link_id] != undefined) {
			url = g_urls[link_id];
			if (g_titles[link_id] != undefined) {
				title = g_titles[link_id];
			}
		}
		else {
			return whole_match;
		}
	}	
	
	alt_text = alt_text.replace(/"/g,"&quot;");
	url = escapeCharacters(url,"*_");
	var result = "<img src=\"" + url + "\" alt=\"" + alt_text + "\"";

	// attacklab: Markdown.pl adds empty title attributes to images.
	// Replicate this bug.

	//if (title != "") {
		title = title.replace(/"/g,"&quot;");
		title = escapeCharacters(title,"*_");
		result +=  " title=\"" + title + "\"";
	//}
	
	result += " />";
	
	return result;
}


var _DoHeaders = function(text) {

	// Setext-style headers:
	//	Header 1
	//	========
	//  
	//	Header 2
	//	--------
	//
	text = text.replace(/^(.+)[ \t]*\n=+[ \t]*\n+/gm,
		function(wholeMatch,m1){return hashBlock("<h1>" + _RunSpanGamut(m1) + "</h1>");});

	text = text.replace(/^(.+)[ \t]*\n-+[ \t]*\n+/gm,
		function(matchFound,m1){return hashBlock("<h2>" + _RunSpanGamut(m1) + "</h2>");});

	// atx-style headers:
	//  # Header 1
	//  ## Header 2
	//  ## Header 2 with closing hashes ##
	//  ...
	//  ###### Header 6
	//

	/*
		text = text.replace(/
			^(\#{1,6})				// $1 = string of #'s
			[ \t]*
			(.+?)					// $2 = Header text
			[ \t]*
			\#*						// optional closing #'s (not counted)
			\n+
		/gm, function() {...});
	*/

	text = text.replace(/^(\#{1,6})[ \t]*(.+?)[ \t]*\#*\n+/gm,
		function(wholeMatch,m1,m2) {
			var h_level = m1.length;
			return hashBlock("<h" + h_level + ">" + _RunSpanGamut(m2) + "</h" + h_level + ">");
		});

	return text;
}

// This declaration keeps Dojo compressor from outputting garbage:
var _ProcessListItems;

var _DoLists = function(text) {
//
// Form HTML ordered (numbered) and unordered (bulleted) lists.
//

	// attacklab: add sentinel to hack around khtml/safari bug:
	// http://bugs.webkit.org/show_bug.cgi?id=11231
	text += "~0";

	// Re-usable pattern to match any entirel ul or ol list:

	/*
		var whole_list = /
		(									// $1 = whole list
			(								// $2
				[ ]{0,3}					// attacklab: g_tab_width - 1
				([*+-]|\d+[.])				// $3 = first list item marker
				[ \t]+
			)
			[^\r]+?
			(								// $4
				~0							// sentinel for workaround; should be $
			|
				\n{2,}
				(?=\S)
				(?!							// Negative lookahead for another list item marker
					[ \t]*
					(?:[*+-]|\d+[.])[ \t]+
				)
			)
		)/g
	*/
	var whole_list = /^(([ ]{0,3}([*+-]|\d+[.])[ \t]+)[^\r]+?(~0|\n{2,}(?=\S)(?![ \t]*(?:[*+-]|\d+[.])[ \t]+)))/gm;

	if (g_list_level) {
		text = text.replace(whole_list,function(wholeMatch,m1,m2) {
			var list = m1;
			var list_type = (m2.search(/[*+-]/g)>-1) ? "ul" : "ol";

			// Turn double returns into triple returns, so that we can make a
			// paragraph for the last item in a list, if necessary:
			list = list.replace(/\n{2,}/g,"\n\n\n");;
			var result = _ProcessListItems(list);
	
			// Trim any trailing whitespace, to put the closing `</$list_type>`
			// up on the preceding line, to get it past the current stupid
			// HTML block parser. This is a hack to work around the terrible
			// hack that is the HTML block parser.
			result = result.replace(/\s+$/,"");
			result = "<"+list_type+">" + result + "</"+list_type+">\n";
			return result;
		});
	} else {
		whole_list = /(\n\n|^\n?)(([ ]{0,3}([*+-]|\d+[.])[ \t]+)[^\r]+?(~0|\n{2,}(?=\S)(?![ \t]*(?:[*+-]|\d+[.])[ \t]+)))/g;
		text = text.replace(whole_list,function(wholeMatch,m1,m2,m3) {
			var runup = m1;
			var list = m2;

			var list_type = (m3.search(/[*+-]/g)>-1) ? "ul" : "ol";
			// Turn double returns into triple returns, so that we can make a
			// paragraph for the last item in a list, if necessary:
			var list = list.replace(/\n{2,}/g,"\n\n\n");;
			var result = _ProcessListItems(list);
			result = runup + "<"+list_type+">\n" + result + "</"+list_type+">\n";	
			return result;
		});
	}

	// attacklab: strip sentinel
	text = text.replace(/~0/,"");

	return text;
}

_ProcessListItems = function(list_str) {
//
//  Process the contents of a single ordered or unordered list, splitting it
//  into individual list items.
//
	// The $g_list_level global keeps track of when we're inside a list.
	// Each time we enter a list, we increment it; when we leave a list,
	// we decrement. If it's zero, we're not in a list anymore.
	//
	// We do this because when we're not inside a list, we want to treat
	// something like this:
	//
	//    I recommend upgrading to version
	//    8. Oops, now this line is treated
	//    as a sub-list.
	//
	// As a single paragraph, despite the fact that the second line starts
	// with a digit-period-space sequence.
	//
	// Whereas when we're inside a list (or sub-list), that line will be
	// treated as the start of a sub-list. What a kludge, huh? This is
	// an aspect of Markdown's syntax that's hard to parse perfectly
	// without resorting to mind-reading. Perhaps the solution is to
	// change the syntax rules such that sub-lists must start with a
	// starting cardinal number; e.g. "1." or "a.".

	g_list_level++;

	// trim trailing blank lines:
	list_str = list_str.replace(/\n{2,}$/,"\n");

	// attacklab: add sentinel to emulate \z
	list_str += "~0";

	/*
		list_str = list_str.replace(/
			(\n)?							// leading line = $1
			(^[ \t]*)						// leading whitespace = $2
			([*+-]|\d+[.]) [ \t]+			// list marker = $3
			([^\r]+?						// list item text   = $4
			(\n{1,2}))
			(?= \n* (~0 | \2 ([*+-]|\d+[.]) [ \t]+))
		/gm, function(){...});
	*/
	list_str = list_str.replace(/(\n)?(^[ \t]*)([*+-]|\d+[.])[ \t]+([^\r]+?(\n{1,2}))(?=\n*(~0|\2([*+-]|\d+[.])[ \t]+))/gm,
		function(wholeMatch,m1,m2,m3,m4){
			var item = m4;
			var leading_line = m1;
			var leading_space = m2;

			if (leading_line || (item.search(/\n{2,}/)>-1)) {
				item = _RunBlockGamut(_Outdent(item));
			}
			else {
				// Recursion for sub-lists:
				item = _DoLists(_Outdent(item));
				item = item.replace(/\n$/,""); // chomp(item)
				item = _RunSpanGamut(item);
			}

			return  "<li>" + item + "</li>\n";
		}
	);

	// attacklab: strip sentinel
	list_str = list_str.replace(/~0/g,"");

	g_list_level--;
	return list_str;
}


var _DoCodeBlocks = function(text) {
//
//  Process Markdown `<pre><code>` blocks.
//  

	/*
		text = text.replace(text,
			/(?:\n\n|^)
			(								// $1 = the code block -- one or more lines, starting with a space/tab
				(?:
					(?:[ ]{4}|\t)			// Lines must start with a tab or a tab-width of spaces - attacklab: g_tab_width
					.*\n+
				)+
			)
			(\n*[ ]{0,3}[^ \t\n]|(?=~0))	// attacklab: g_tab_width
		/g,function(){...});
	*/

	// attacklab: sentinel workarounds for lack of \A and \Z, safari\khtml bug
	text += "~0";
	
	text = text.replace(/(?:\n\n|^)((?:(?:[ ]{4}|\t).*\n+)+)(\n*[ ]{0,3}[^ \t\n]|(?=~0))/g,
		function(wholeMatch,m1,m2) {
			var codeblock = m1;
			var nextChar = m2;
		
			codeblock = _EncodeCode( _Outdent(codeblock));
			codeblock = _Detab(codeblock);
			codeblock = codeblock.replace(/^\n+/g,""); // trim leading newlines
			codeblock = codeblock.replace(/\n+$/g,""); // trim trailing whitespace

			codeblock = "<pre><code>" + codeblock + "\n</code></pre>";

			return hashBlock(codeblock) + nextChar;
		}
	);

	// attacklab: strip sentinel
	text = text.replace(/~0/,"");

	return text;
}

var hashBlock = function(text) {
	text = text.replace(/(^\n+|\n+$)/g,"");
	return "\n\n~K" + (g_html_blocks.push(text)-1) + "K\n\n";
}


var _DoCodeSpans = function(text) {
//
//   *  Backtick quotes are used for <code></code> spans.
// 
//   *  You can use multiple backticks as the delimiters if you want to
//	 include literal backticks in the code span. So, this input:
//	 
//		 Just type ``foo `bar` baz`` at the prompt.
//	 
//	   Will translate to:
//	 
//		 <p>Just type <code>foo `bar` baz</code> at the prompt.</p>
//	 
//	There's no arbitrary limit to the number of backticks you
//	can use as delimters. If you need three consecutive backticks
//	in your code, use four for delimiters, etc.
//
//  *  You can use spaces to get literal backticks at the edges:
//	 
//		 ... type `` `bar` `` ...
//	 
//	   Turns to:
//	 
//		 ... type <code>`bar`</code> ...
//

	/*
		text = text.replace(/
			(^|[^\\])					// Character before opening ` can't be a backslash
			(`+)						// $2 = Opening run of `
			(							// $3 = The code block
				[^\r]*?
				[^`]					// attacklab: work around lack of lookbehind
			)
			\2							// Matching closer
			(?!`)
		/gm, function(){...});
	*/

	text = text.replace(/(^|[^\\])(`+)([^\r]*?[^`])\2(?!`)/gm,
		function(wholeMatch,m1,m2,m3,m4) {
			var c = m3;
			c = c.replace(/^([ \t]*)/g,"");	// leading whitespace
			c = c.replace(/[ \t]*$/g,"");	// trailing whitespace
			c = _EncodeCode(c);
			return m1+"<code>"+c+"</code>";
		});

	return text;
}


var _EncodeCode = function(text) {
//
// Encode/escape certain characters inside Markdown code runs.
// The point is that in code, these characters are literals,
// and lose their special Markdown meanings.
//
	// Encode all ampersands; HTML entities are not
	// entities within a Markdown code span.
	text = text.replace(/&/g,"&amp;");

	// Do the angle bracket song and dance:
	text = text.replace(/</g,"&lt;");
	text = text.replace(/>/g,"&gt;");

	// Now, escape characters that are magic in Markdown:
	text = escapeCharacters(text,"\*_{}[]\\",false);

// jj the line above breaks this:
//---

//* Item

//   1. Subitem

//            special char: *
//---

	return text;
}


var _DoItalicsAndBold = function(text) {

	// <strong> must go first:
	text = text.replace(/(\*\*|__)(?=\S)([^\r]*?\S[\*_]*)\1/g,
		"<strong>$2</strong>");

	text = text.replace(/(\*|_)(?=\S)([^\r]*?\S)\1/g,
		"<em>$2</em>");

	return text;
}


var _DoBlockQuotes = function(text) {

	/*
		text = text.replace(/
		(								// Wrap whole match in $1
			(
				^[ \t]*>[ \t]?			// '>' at the start of a line
				.+\n					// rest of the first line
				(.+\n)*					// subsequent consecutive lines
				\n*						// blanks
			)+
		)
		/gm, function(){...});
	*/

	text = text.replace(/((^[ \t]*>[ \t]?.+\n(.+\n)*\n*)+)/gm,
		function(wholeMatch,m1) {
			var bq = m1;

			// attacklab: hack around Konqueror 3.5.4 bug:
			// "----------bug".replace(/^-/g,"") == "bug"

			bq = bq.replace(/^[ \t]*>[ \t]?/gm,"~0");	// trim one level of quoting

			// attacklab: clean up hack
			bq = bq.replace(/~0/g,"");

			bq = bq.replace(/^[ \t]+$/gm,"");		// trim whitespace-only lines
			bq = _RunBlockGamut(bq);				// recurse
			
			bq = bq.replace(/(^|\n)/g,"$1  ");
			// These leading spaces screw with <pre> content, so we need to fix that:
			bq = bq.replace(
					/(\s*<pre>[^\r]+?<\/pre>)/gm,
				function(wholeMatch,m1) {
					var pre = m1;
					// attacklab: hack around Konqueror 3.5.4 bug:
					pre = pre.replace(/^  /mg,"~0");
					pre = pre.replace(/~0/g,"");
					return pre;
				});
			
			return hashBlock("<blockquote>\n" + bq + "\n</blockquote>");
		});
	return text;
}


var _FormParagraphs = function(text) {
//
//  Params:
//    $text - string to process with html <p> tags
//

	// Strip leading and trailing lines:
	text = text.replace(/^\n+/g,"");
	text = text.replace(/\n+$/g,"");

	var grafs = text.split(/\n{2,}/g);
	var grafsOut = new Array();

	//
	// Wrap <p> tags.
	//
	var end = grafs.length;
	for (var i=0; i<end; i++) {
		var str = grafs[i];

		// if this is an HTML marker, copy it
		if (str.search(/~K(\d+)K/g) >= 0) {
			grafsOut.push(str);
		}
		else if (str.search(/\S/) >= 0) {
			str = _RunSpanGamut(str);
			str = str.replace(/^([ \t]*)/g,"<p>");
			str += "</p>"
			grafsOut.push(str);
		}

	}

	//
	// Unhashify HTML blocks
	//
	end = grafsOut.length;
	for (var i=0; i<end; i++) {
		// if this is a marker for an html block...
		while (grafsOut[i].search(/~K(\d+)K/) >= 0) {
			var blockText = g_html_blocks[RegExp.$1];
			blockText = blockText.replace(/\$/g,"$$$$"); // Escape any dollar signs
			grafsOut[i] = grafsOut[i].replace(/~K\d+K/,blockText);
		}
	}

	return grafsOut.join("\n\n");
}


var _EncodeAmpsAndAngles = function(text) {
// Smart processing for ampersands and angle brackets that need to be encoded.
	
	// Ampersand-encoding based entirely on Nat Irons's Amputator MT plugin:
	//   http://bumppo.net/projects/amputator/
	text = text.replace(/&(?!#?[xX]?(?:[0-9a-fA-F]+|\w+);)/g,"&amp;");
	
	// Encode naked <'s
	text = text.replace(/<(?![a-z\/?\$!])/gi,"&lt;");
	
	return text;
}


var _EncodeBackslashEscapes = function(text) {
//
//   Parameter:  String.
//   Returns:	The string, with after processing the following backslash
//			   escape sequences.
//

	// attacklab: The polite way to do this is with the new
	// escapeCharacters() function:
	//
	// 	text = escapeCharacters(text,"\\",true);
	// 	text = escapeCharacters(text,"`*_{}[]()>#+-.!",true);
	//
	// ...but we're sidestepping its use of the (slow) RegExp constructor
	// as an optimization for Firefox.  This function gets called a LOT.

	text = text.replace(/\\(\\)/g,escapeCharacters_callback);
	text = text.replace(/\\([`*_{}\[\]()>#+-.!])/g,escapeCharacters_callback);
	return text;
}


var _DoAutoLinks = function(text) {

	text = text.replace(/<((https?|ftp|dict):[^'">\s]+)>/gi,"<a href=\"$1\">$1</a>");

	// Email addresses: <address@domain.foo>

	/*
		text = text.replace(/
			<
			(?:mailto:)?
			(
				[-.\w]+
				\@
				[-a-z0-9]+(\.[-a-z0-9]+)*\.[a-z]+
			)
			>
		/gi, _DoAutoLinks_callback());
	*/
	text = text.replace(/<(?:mailto:)?([-.\w]+\@[-a-z0-9]+(\.[-a-z0-9]+)*\.[a-z]+)>/gi,
		function(wholeMatch,m1) {
			return _EncodeEmailAddress( _UnescapeSpecialChars(m1) );
		}
	);

	return text;
}


var _EncodeEmailAddress = function(addr) {
//
//  Input: an email address, e.g. "foo@example.com"
//
//  Output: the email address as a mailto link, with each character
//	of the address encoded as either a decimal or hex entity, in
//	the hopes of foiling most address harvesting spam bots. E.g.:
//
//	<a href="&#x6D;&#97;&#105;&#108;&#x74;&#111;:&#102;&#111;&#111;&#64;&#101;
//	   x&#x61;&#109;&#x70;&#108;&#x65;&#x2E;&#99;&#111;&#109;">&#102;&#111;&#111;
//	   &#64;&#101;x&#x61;&#109;&#x70;&#108;&#x65;&#x2E;&#99;&#111;&#109;</a>
//
//  Based on a filter by Matthew Wickline, posted to the BBEdit-Talk
//  mailing list: <http://tinyurl.com/yu7ue>
//

	// attacklab: why can't javascript speak hex?
	function char2hex(ch) {
		var hexDigits = '0123456789ABCDEF';
		var dec = ch.charCodeAt(0);
		return(hexDigits.charAt(dec>>4) + hexDigits.charAt(dec&15));
	}

	var encode = [
		function(ch){return "&#"+ch.charCodeAt(0)+";";},
		function(ch){return "&#x"+char2hex(ch)+";";},
		function(ch){return ch;}
	];

	addr = "mailto:" + addr;

	addr = addr.replace(/./g, function(ch) {
		if (ch == "@") {
		   	// this *must* be encoded. I insist.
			ch = encode[Math.floor(Math.random()*2)](ch);
		} else if (ch !=":") {
			// leave ':' alone (to spot mailto: later)
			var r = Math.random();
			// roughly 10% raw, 45% hex, 45% dec
			ch =  (
					r > .9  ?	encode[2](ch)   :
					r > .45 ?	encode[1](ch)   :
								encode[0](ch)
				);
		}
		return ch;
	});

	addr = "<a href=\"" + addr + "\">" + addr + "</a>";
	addr = addr.replace(/">.+:/g,"\">"); // strip the mailto: from the visible part

	return addr;
}


var _UnescapeSpecialChars = function(text) {
//
// Swap back in all the special characters we've hidden.
//
	text = text.replace(/~E(\d+)E/g,
		function(wholeMatch,m1) {
			var charCodeToReplace = parseInt(m1);
			return String.fromCharCode(charCodeToReplace);
		}
	);
	return text;
}


var _Outdent = function(text) {
//
// Remove one level of line-leading tabs or spaces
//

	// attacklab: hack around Konqueror 3.5.4 bug:
	// "----------bug".replace(/^-/g,"") == "bug"

	text = text.replace(/^(\t|[ ]{1,4})/gm,"~0"); // attacklab: g_tab_width

	// attacklab: clean up hack
	text = text.replace(/~0/g,"")

	return text;
}

var _Detab = function(text) {
// attacklab: Detab's completely rewritten for speed.
// In perl we could fix it by anchoring the regexp with \G.
// In javascript we're less fortunate.

	// expand first n-1 tabs
	text = text.replace(/\t(?=\t)/g,"    "); // attacklab: g_tab_width

	// replace the nth with two sentinels
	text = text.replace(/\t/g,"~A~B");

	// use the sentinel to anchor our regex so it doesn't explode
	text = text.replace(/~B(.+?)~A/g,
		function(wholeMatch,m1,m2) {
			var leadingText = m1;
			var numSpaces = 4 - leadingText.length % 4;  // attacklab: g_tab_width

			// there *must* be a better way to do this:
			for (var i=0; i<numSpaces; i++) leadingText+=" ";

			return leadingText;
		}
	);

	// clean up sentinels
	text = text.replace(/~A/g,"    ");  // attacklab: g_tab_width
	text = text.replace(/~B/g,"");

	return text;
}


//
//  attacklab: Utility functions
//


var escapeCharacters = function(text, charsToEscape, afterBackslash) {
	// First we have to escape the escape characters so that
	// we can build a character class out of them
	var regexString = "([" + charsToEscape.replace(/([\[\]\\])/g,"\\$1") + "])";

	if (afterBackslash) {
		regexString = "\\\\" + regexString;
	}

	var regex = new RegExp(regexString,"g");
	text = text.replace(regex,escapeCharacters_callback);

	return text;
}


var escapeCharacters_callback = function(wholeMatch,m1) {
	var charCodeToEscape = m1.charCodeAt(0);
	return "~E"+charCodeToEscape+"E";
}

} // end of Attacklab.showdown.converter




//---------------------------------------------------------------------------------------------------------------------------------







var mooWMD={
	/**
	 * Configuration values
	 */
	Config:{
		/**
		 * The text that appears on the upper part of the dialog box when
		 * entering links.
		 */
		imageDialogText: "<p style='margin-top: 0px'><b>Enter the image URL.</b></p><p>You can also add a title, which will be displayed as a tool tip.</p><p>Example:<br />http://wmd-editor.com/images/cloud1.jpg   \"Optional title\"</p>",
		linkDialogText: "<p style='margin-top: 0px'><b>Enter the web address.</b></p><p>You can also add a title, which will be displayed as a tool tip.</p><p>Example:<br />http://wmd-editor.com/   \"Optional title\"</p>",
		imageDirectory: 'images/',
		/**
		 * The default text that appears in the dialog input box when entering
		 * links.
		 */
		imageDefaultText: "http://",
		linkDefaultText: "http://",
		/**
		 * Some texts for the HELP link
		 */
		helpLink: "http://wmd-editor.com/",
		helpHoverTitle: "WMD website",
		helpTarget: "_blank",
		/**
		 * Intervals
		 * Should be adjusted to tune editor load
		 */
		previewPollInterval: 500,
		pastePollInterval:100,
		
		//Currently, not used!!!
		defaultButtons: "bold italic link blockquote code image ol ul heading hr",
		version:3,
		output:"HTML",
		lineLength:40,
		delayLoad:false
	},//EOF Config
	
	/**
	 * Utility functions which does not need state
	 */
	Utils:{
		/**
		 * is Visible 
		 */
		isVisible: function (obj){//(elem) {
			if (obj == document) return true

			if (!obj) return false
			if (!obj.parentNode) return false
			if (obj.style) {
				if (obj.style.display == 'none') return false
				if (obj.style.visibility == 'hidden') return false
			}

			//Try the computed style in a standard way
			if (window.getComputedStyle) {
				var style = window.getComputedStyle(obj, "")
				if (style.display == 'none') return false
				if (style.visibility == 'hidden') return false
			}

			//Or get the computed style using IE's silly proprietary way
			var style = obj.currentStyle
			if (style) {
				if (style['display'] == 'none') return false
				if (style['visibility'] == 'hidden') return false
			}
			return this.isVisible(obj.parentNode)
			
			/*
			if (window.getComputedStyle) {
				// Most browsers
				return window.getComputedStyle(elem, null).getPropertyValue("display") !== "none";
			}
			else if (elem.currentStyle) {
				// IE
				return elem.currentStyle["display"] !== "none";
			}
			*/
		},//EOF Utils.isVisible
		
		/**
		 * Converts \r\n and \r to \n.
		 */
		fixEolChars: function(text){
			text = text.replace(/\r\n/g, "\n");
			text = text.replace(/\r/g, "\n");
			return text;
		},//EOF fixEolChars
		
		/**
		 * Extends a regular expression.  Returns a new RegExp
		 * using pre + regex + post as the expression.
		 * Used in a few functions where we have a base
		 * expression and we want to pre- or append some
		 * conditions to it (e.g. adding "$" to the end).
		 * The flags are unchanged.
		 * 
		 * regex is a RegExp, pre and post are strings.
		 */
		extendRegExp: function(regex, pre, post){
			if (pre === null || pre === undefined){
				pre = "";
			}
			if(post === null || post === undefined){
				post = "";
			}
			var pattern = regex.toString();
			var flags = "";
			// Replace the flags with empty space and store them.
			// Technically, this can match incorrect flags like "gmm".
			var result = pattern.match(/\/([gim]*)$/);
			if (result === null) {
				flags = result[0];
			}else{
				flags = "";
			}
			// Remove the flags and slash delimiters from the regular expression.
			pattern = pattern.replace(/(^\/|\/[gim]*$)/g, "");
			pattern = pre + pattern + post;
			return new RegExp(pattern, flags);
		},//EOF extendRegExp
		
		/**
		 * TODO: IT SEEMS THIS ISN'T BEING USED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
		 * 
		 * Sets the image for a button passed to the WMD editor.
		 * Returns a new element with the image attached.
		 * Adds several style properties to the image.
		 */
		createImage:function(img){
			var elm = new Element('img',{class:'wmd-button',
										 src: (mooWMD.Config.imageDirectory + img)
								});
			return elm;
		}//EOF createImage
	},//EOF Utils function collection
	
	/**
	 * Holds the entire text in the textarea. Purpose: to enter tags into it.
	 */
	Chunk: new Class({
		/**
		 * contains all the text in the input box BEFORE the selection.
		 */
		before:'',
		startTag:'',
		selection:'',
		endTag:'',
		prefixes: "(?:\\s{4,}|\\s*>|\\s*-\\s+|\\s*\\d+\\.|=|\\+|-|_|\\*|#|\\s*\\[[^\n]]+\\]:)",		// The markdown symbols - 4 spaces = code, > = blockquote, etc.

		/**
		 * contains all the text in the input box AFTER the selection.
		 */
		after:'',
		scrollTop:0,
		initialize: function(StateObj){
			this.before = mooWMD.Utils.fixEolChars(StateObj.text.substring(0, StateObj.start));
			this.selection = mooWMD.Utils.fixEolChars(StateObj.text.substring(StateObj.start, StateObj.end));
			this.after = mooWMD.Utils.fixEolChars(StateObj.text.substring(StateObj.end));
			this.scrollTop = StateObj.scrollTop;
		},//EOF mooWMD.Chunk.initialize
		
		/**
		 * startRegex: a regular expression to find the start tag
		 * endRegex: a regular expresssion to find the end tag
		 */
		findTags: function(startRegex, endRegex){
			var regex;
			if (startRegex) {
				regex = mooWMD.Utils.extendRegExp(startRegex, "", "$");
				this.before = this.before.replace(regex, 
					function(match){
						this.startTag = this.startTag + match;
						return "";
					});
				
				regex = mooWMD.Utils.extendRegExp(startRegex, "^", "");
				
				this.selection = this.selection.replace(regex, 
					function(match){
						this.startTag = this.startTag + match;
						return "";
					});
			}			
			if (endRegex) {
				regex = mooWMD.Utils.extendRegExp(endRegex, "", "$");
				this.selection = this.selection.replace(regex,
					function(match){
						this.endTag = match + this.endTag;
						return "";
					});
				regex = mooWMD.Utils.extendRegExp(endRegex, "^", "");
				this.after = this.after.replace(regex,
					function(match){
						this.endTag = match + this.endTag;
						return "";
					});
			}
		},//EOF mooWMD.Chunk.findTags

		/**
		 * If remove is false, the whitespace is transferred
		 * to the before/after regions.
		 * 
		 * If remove is true, the whitespace disappears.
		 */
		trimWhitespace: function(remove){
			this.selection = this.selection.replace(/^(\s*)/, "");
			if (!remove) {
				this.before += RegExp.$1;
			}
			this.selection = this.selection.replace(/(\s*)$/, "");
			if (!remove) {
				this.after = RegExp.$1 + this.after;
			}
		},//EOF mooWMD.Chunk.trimWhitespace

		/**
		 * 
		 */
		addBlankLines: function(nLinesBefore, nLinesAfter, findExtraNewlines){
		
			if (nLinesBefore === undefined) {
				nLinesBefore = 1;
			}
			
			if (nLinesAfter === undefined) {
				nLinesAfter = 1;
			}
			
			nLinesBefore++;
			nLinesAfter++;
			
			var regexText;
			var replacementText;
			
			this.selection = this.selection.replace(/(^\n*)/, "");
			this.startTag = this.startTag + RegExp.$1;
			this.selection = this.selection.replace(/(\n*$)/, "");
			this.endTag = this.endTag + RegExp.$1;
			this.startTag = this.startTag.replace(/(^\n*)/, "");
			this.before = this.before + RegExp.$1;
			this.endTag = this.endTag.replace(/(\n*$)/, "");
			this.after = this.after + RegExp.$1;
			if (this.before) {
				regexText = replacementText = "";
				while (nLinesBefore--) {
					regexText += "\\n?";
					replacementText += "\n";
				}
				if (findExtraNewlines) {
					regexText = "\\n*";
				}
				this.before = this.before.replace(new RegExp(regexText + "$", ""), replacementText);
			}
			
			if (this.after) {
				regexText = replacementText = "";
				while (nLinesAfter--) {
					regexText += "\\n?";
					replacementText += "\n";
				}
				if (findExtraNewlines) {
					regexText = "\\n*";
				}
				this.after = this.after.replace(new RegExp(regexText, ""), replacementText);
			}
		},//EOF mooWMD.Chunk.addBlankLines
		
		/**
		 * 
		 */
		wrap: function(len){
			this.unwrap();
			var regex = new RegExp("(.{1," + len + "})( +|$\\n?)", "gm");
			
			this.selection = this.selection.replace(regex, function(line, marked){
				if (new RegExp("^" + this.prefixes, "").test(line)) {
					return line;
				}
				return marked + "\n";
			}.bind(this));
			
			this.selection = this.selection.replace(/\s+$/, "");
		},//EOF mooWMD.Chunk.wrap
		
		/**
		 * Remove markdown symbols from the chunk selection.
		 */
		unwrap: function(){
			var txt = new RegExp("([^\\n])\\n(?!(\\n|" + this.prefixes + "))", "g");
			this.selection = this.selection.replace(txt, "$1 $2");
		}//EOF mooWMD.Chunk.unwrap
	}),//EOF mooWMD.Chunk


	/**
	 * Buttons
	 * 
	 * @postfix: A string to add to the end of the ID of the elements. Will enable us to use multiple editors on same page.
	 */
	SpritedButtonRow: new Class({
		postfix:'', //postfix for the IDs of the buttons, will enable me to use multiple editors.
		undoMgr: null,
		previewRefreshCallback: null, //Callback method to do after a button clicked?
		input: null,
		editObj: null, //Editor object
		
		initialize: function(postfix,previewRefreshCallback,input,editObj){
			this.postfix=postfix;
			this.previewRefreshCallback=previewRefreshCallback;
			this.input=input;
			this.editObj=editObj;
			this.input.addEvent('keydown',this.addButtonActionsToInputBox.bind(this));
		},//EOF mooWMD.SpritedButtonRow.initialize
		
		/**
		 * 
		 */
		build: function(){
			var buttonBar = $('wmd-button-bar'+this.postfix);//TODO in later version, user will have to only put a textarea.
 			var normalYShift = "0px";
			var disabledYShift = "-20px";
			var highlightYShift = "-40px";
			
			var buttonRow = new Element("ul");
			buttonRow.id = "wmd-button-row"+this.postfix;
			buttonRow.className = "wmd-button-row";
			buttonBar.adopt(buttonRow);

			
			var boldButton = document.createElement("li");
			boldButton.className = "wmd-button wmd-bold-button";
			boldButton.id = "wmd-bold-button"+this.postfix;
			boldButton.title = "Strong <strong> Ctrl+B";
			boldButton.XShift = "0px";
			boldButton.textOp = this.doBold.bind(this);
			this.setupButton(boldButton, true);
			buttonRow.adopt(boldButton);
			
			var italicButton = new Element("li");
			italicButton.className = "wmd-button wmd-italic-button";
			italicButton.id = "wmd-italic-button"+this.postfix;
			italicButton.title = "Emphasis <em> Ctrl+I";
			italicButton.XShift = "-20px";
			italicButton.textOp = this.doItalic.bind(this);
			this.setupButton(italicButton, true);
			buttonRow.adopt(italicButton);


			var spacer1 = new Element("li");
			spacer1.className = "wmd-button wmd-spacer1";
			buttonRow.adopt(spacer1); 

			var linkButton = new Element("li");
			linkButton.className = "wmd-button wmd-link-button";
			linkButton.id = "wmd-link-button"+this.postfix;
			linkButton.title = "Hyperlink <a> Ctrl+L";
			linkButton.XShift = "-40px";
			linkButton.textOp = function(chunk, postProcessing, useDefaultText){
				var MyPrompt=new mooWMD.Prompt(chunk, postProcessing,false);
				return MyPrompt.doLinkOrImage();
			};
			this.setupButton(linkButton, true);
			buttonRow.adopt(linkButton);

			var quoteButton = new Element("li");
			quoteButton.className = "wmd-button wmd-quote-button";
			quoteButton.id = "wmd-quote-button"+this.postfix;
			quoteButton.title = "Blockquote <blockquote> Ctrl+Q";
			quoteButton.XShift = "-60px";
			quoteButton.textOp = this.doBlockquote;
			this.setupButton(quoteButton, true);
			buttonRow.adopt(quoteButton);
			
			var codeButton = new Element("li");
			codeButton.className = "wmd-button wmd-code-button";
			codeButton.id = "wmd-code-button"+this.postfix;
			codeButton.title = "Code Sample <pre><code> Ctrl+K";
			codeButton.XShift = "-80px";
			codeButton.textOp = this.doCode;
			this.setupButton(codeButton, true);
			buttonRow.adopt(codeButton);

			var imageButton = new Element("li");
			imageButton.className = "wmd-button wmd-image-button";
			imageButton.id = "wmd-image-button"+this.postfix;
			imageButton.title = "Image <img> Ctrl+G";
			imageButton.XShift = "-100px";
			imageButton.textOp = function(chunk, postProcessing, useDefaultText){
				var MyPrompt=new mooWMD.Prompt(chunk, postProcessing,true);
				return MyPrompt.doLinkOrImage();
			};
			this.setupButton(imageButton, true);
			buttonRow.adopt(imageButton);
			
			var spacer2 = new Element("li");
			spacer2.className = "wmd-button wmd-spacer2";
			buttonRow.adopt(spacer2); 

			var olistButton = new Element("li");
			olistButton.className = "wmd-button wmd-olist-button";
			olistButton.id = "wmd-olist-button"+this.postfix;
			olistButton.title = "Numbered List <ol> Ctrl+O";
			olistButton.XShift = "-120px";
			olistButton.textOp = function(chunk, postProcessing, useDefaultText){
				this.doList(chunk, postProcessing, true, useDefaultText);
			}.bind(this);
			this.setupButton(olistButton, true);
			buttonRow.adopt(olistButton);
			
			var ulistButton = new Element("li");
			ulistButton.className = "wmd-button wmd-ulist-button";
			ulistButton.id = "wmd-ulist-button"+this.postfix;
			ulistButton.title = "Bulleted List <ul> Ctrl+U";
			ulistButton.XShift = "-140px";
			ulistButton.textOp = function(chunk, postProcessing, useDefaultText){
				this.doList(chunk, postProcessing, false, useDefaultText);
			}.bind(this);
			this.setupButton(ulistButton, true);
			buttonRow.adopt(ulistButton);
			
			var headingButton = new Element("li");
			headingButton.className = "wmd-button wmd-heading-button";
			headingButton.id = "wmd-heading-button"+this.postfix;
			headingButton.title = "Heading <h1>/<h2> Ctrl+H";
			headingButton.XShift = "-160px";
			headingButton.textOp = this.doHeading;
			this.setupButton(headingButton, true);
			buttonRow.adopt(headingButton); 
			
			var hrButton = new Element("li");
			hrButton.className = "wmd-button wmd-hr-button";
			hrButton.id = "wmd-hr-button"+this.postfix;
			hrButton.title = "Horizontal Rule <hr> Ctrl+R";
			hrButton.XShift = "-180px";
			hrButton.textOp = this.doHorizontalRule;
			this.setupButton(hrButton, true);
			buttonRow.adopt(hrButton); 

			var spacer3 = new Element("li");
			spacer3.className = "wmd-button wmd-spacer3";
			buttonRow.adopt(spacer3); 

			var undoButton = new Element("li");
			undoButton.className = "wmd-button wmd-undo-button";
			undoButton.id = "wmd-undo-button"+this.postfix;
			undoButton.title = "Undo - Ctrl+Z";
			undoButton.XShift = "-200px";
			undoButton.execute = function(){
				this.undoMgr.undo();
			}.bind(this);
			this.setupButton(undoButton, true);
			buttonRow.adopt(undoButton); 
			
			var redoButton = new Element("li");
			redoButton.className = "wmd-button wmd-redo-button";
			redoButton.id = "wmd-redo-button"+this.postfix;
			redoButton.title = "Redo - Ctrl+Y";
			if (Browser.Platform.win) {
				redoButton.title = "Redo - Ctrl+Y";
			}else {
				redoButton.title = "Redo - Ctrl+Shift+Z";
			}
			redoButton.XShift = "-220px";
			redoButton.execute = function(){
				this.undoMgr.redo();
			}.bind(this);
			this.setupButton(redoButton, true);
			buttonRow.adopt(redoButton); 
			
			var helpButton = new Element("li");
			helpButton.className = "wmd-button wmd-help-button";
			helpButton.id = "wmd-help-button"+this.postfix;
			helpButton.XShift = "-240px";
			helpButton.isHelp = true;
			
			var helpAnchor = new Element("a");
			helpAnchor.href = mooWMD.Config.helpLink;
			helpAnchor.target = mooWMD.Config.helpTarget
			helpAnchor.title = mooWMD.Config.helpHoverTitle;
			helpButton.adopt(helpAnchor);
			this.setupButton(helpButton, true);
			buttonRow.adopt(helpButton);
			
			this.setUndoRedoButtonStates();
		},//EOF mooWMD.SpritedButtonRow.build
		doBold: function(chunk, postProcessing, useDefaultText){
			return this.doBorI(chunk, 2, "strong text");
		},//EOF mooWMD.SpritedButtonRow.doBold
		doItalic: function(chunk, postProcessing, useDefaultText){
			return this.doBorI(chunk, 1, "emphasized text");
		},//EOF mooWMD.SpritedButtonRow.doItalic
		
		/**
		 * chunk: The selected region that will be enclosed with * / **
		 * nStars: 1 for italics, 2 for bold
		 * insertText: If you just click the button without highlighting text, this gets inserted
		 */
		doBorI: function(chunk, nStars, insertText){
			// Get rid of whitespace and fixup newlines.
			chunk.trimWhitespace();
			chunk.selection = chunk.selection.replace(/\n{2,}/g, "\n");
			
			// Look for stars before and after.  Is the chunk already marked up?
			chunk.before.search(/(\**$)/);
			var starsBefore = RegExp.$1;
			chunk.after.search(/(^\**)/);
			var starsAfter = RegExp.$1;
			var prevStars = Math.min(starsBefore.length, starsAfter.length);
			
			// Remove stars if we have to since the button acts as a toggle.
			if ((prevStars >= nStars) && (prevStars != 2 || nStars != 1)) {
				chunk.before = chunk.before.replace(re("[*]{" + nStars + "}$", ""), "");
				chunk.after = chunk.after.replace(re("^[*]{" + nStars + "}", ""), "");
			}
			else if (!chunk.selection && starsAfter) {
				// It's not really clear why this code is necessary.  It just moves
				// some arbitrary stuff around.
				chunk.after = chunk.after.replace(/^([*_]*)/, "");
				chunk.before = chunk.before.replace(/(\s?)$/, "");
				var whitespace = RegExp.$1;
				chunk.before = chunk.before + starsAfter + whitespace;
			}
			else {
			
				// In most cases, if you don't have any selected text and click the button
				// you'll get a selected, marked up region with the default text inserted.
				if (!chunk.selection && !starsAfter) {
					chunk.selection = insertText;
				}
				
				// Add the true markup.
				var markup = nStars <= 1 ? "*" : "**"; // shouldn't the test be = ?
				chunk.before = chunk.before + markup;
				chunk.after = markup + chunk.after;
			}
			return;
		},//EOF mooWMD.SpritedButtonRow.doBorI

		/**
		 * 
		 */
		doBlockquote: function(chunk, postProcessing, useDefaultText){
			chunk.selection = chunk.selection.replace(/^(\n*)([^\r]+?)(\n*)$/,
				function(totalMatch, newlinesBefore, text, newlinesAfter){
					chunk.before += newlinesBefore;
					chunk.after = newlinesAfter + chunk.after;
					return text;
				});
				
			chunk.before = chunk.before.replace(/(>[ \t]*)$/,
				function(totalMatch, blankLine){
					chunk.selection = blankLine + chunk.selection;
					return "";
				});
			
			var defaultText = useDefaultText ? "Blockquote" : "";
			chunk.selection = chunk.selection.replace(/^(\s|>)+$/ ,"");
			chunk.selection = chunk.selection || defaultText;
			
			if(chunk.before){
				chunk.before = chunk.before.replace(/\n?$/,"\n");
			}
			if(chunk.after){
				chunk.after = chunk.after.replace(/^\n?/,"\n");
			}
			
			chunk.before = chunk.before.replace(/(((\n|^)(\n[ \t]*)*>(.+\n)*.*)+(\n[ \t]*)*$)/,
				function(totalMatch){
					chunk.startTag = totalMatch;
					return "";
				});
				
			chunk.after = chunk.after.replace(/^(((\n|^)(\n[ \t]*)*>(.+\n)*.*)+(\n[ \t]*)*)/,
				function(totalMatch){
					chunk.endTag = totalMatch;
					return "";
				});
			
			var replaceBlanksInTags = function(useBracket){
				var replacement = useBracket ? "> " : "";
				if(chunk.startTag){
					chunk.startTag = chunk.startTag.replace(/\n((>|\s)*)\n$/,
						function(totalMatch, markdown){
							return "\n" + markdown.replace(/^[ ]{0,3}>?[ \t]*$/gm, replacement) + "\n";
						});
				}
				if(chunk.endTag){
					chunk.endTag = chunk.endTag.replace(/^\n((>|\s)*)\n/,
						function(totalMatch, markdown){
							return "\n" + markdown.replace(/^[ ]{0,3}>?[ \t]*$/gm, replacement) + "\n";
						});
				}
			};
			
			if(/^(?![ ]{0,3}>)/m.test(chunk.selection)){
				command.wrap(chunk, mooWMD.Config.lineLength - 2);
				chunk.selection = chunk.selection.replace(/^/gm, "> ");
				replaceBlanksInTags(true);
				chunk.addBlankLines();
			}
			else{
				chunk.selection = chunk.selection.replace(/^[ ]{0,3}> ?/gm, "");
				chunk.unwrap();
				replaceBlanksInTags(false);
				
				if(!/^(\n|^)[ ]{0,3}>/.test(chunk.selection) && chunk.startTag){
					chunk.startTag = chunk.startTag.replace(/\n{0,2}$/, "\n\n");
				}
				
				if(!/(\n|^)[ ]{0,3}>.*$/.test(chunk.selection) && chunk.endTag){
					chunk.endTag=chunk.endTag.replace(/^\n{0,2}/, "\n\n");
				}
			}
			
			if(!/\n/.test(chunk.selection)){
				chunk.selection = chunk.selection.replace(/^(> *)/,
				function(wholeMatch, blanks){
					chunk.startTag += blanks;
					return "";
				});
			}
		},//EOF mooWMD.SpritedButtonRow.doBlockQuote

		/**
		 * 
		 */		
		doCode: function(chunk, postProcessing, useDefaultText){
			var hasTextBefore = /\S[ ]*$/.test(chunk.before);
			var hasTextAfter = /^[ ]*\S/.test(chunk.after);
			
			// Use 'four space' markdown if the selection is on its own
			// line or is multiline.
			if((!hasTextAfter && !hasTextBefore) || /\n/.test(chunk.selection)){
				chunk.before = chunk.before.replace(/[ ]{4}$/,
					function(totalMatch){
						chunk.selection = totalMatch + chunk.selection;
						return "";
					});
				var nLinesBefore = 1;
				var nLinesAfter = 1;
				if(/\n(\t|[ ]{4,}).*\n$/.test(chunk.before) || chunk.after === ""){
					nLinesBefore = 0; 
				}
				if(/^\n(\t|[ ]{4,})/.test(chunk.after)){
					nLinesAfter = 0; // This needs to happen on line 1
				}
				chunk.addBlankLines(nLinesBefore, nLinesAfter);
				if(!chunk.selection){
					chunk.startTag = "    ";
					chunk.selection = useDefaultText ? "enter code here" : "";
				}
				else {
					if(/^[ ]{0,3}\S/m.test(chunk.selection)){
						chunk.selection = chunk.selection.replace(/^/gm, "    ");
					}
					else{
						chunk.selection = chunk.selection.replace(/^[ ]{4}/gm, "");
					}
				}
			}
			else{
				// Use backticks (`) to delimit the code block.
				chunk.trimWhitespace();
				chunk.findTags(/`/, /`/);
				if(!chunk.startTag && !chunk.endTag){
					chunk.startTag = chunk.endTag="`";
					if(!chunk.selection){
						chunk.selection = useDefaultText ? "enter code here" : "";
					}
				}
				else if(chunk.endTag && !chunk.startTag){
					chunk.before += chunk.endTag;
					chunk.endTag = "";
				}
				else{
					chunk.startTag = chunk.endTag="";
				}
			}
		},//EOF mooWMD.SpritedButtonRow.doCode
		
		/**
		 * 
		 */
		doHeading: function(chunk, postProcessing, useDefaultText){
			// Remove leading/trailing whitespace and reduce internal spaces to single spaces.
			chunk.selection = chunk.selection.replace(/\s+/g, " ");
			chunk.selection = chunk.selection.replace(/(^\s+|\s+$)/g, "");
			
			// If we clicked the button with no selected text, we just
			// make a level 2 hash header around some default text.
			if(!chunk.selection){
				chunk.startTag = "## ";
				chunk.selection = "Heading";
				chunk.endTag = " ##";
				return;
			}
			var headerLevel = 0;		// The existing header level of the selected text.
			// Remove any existing hash heading markdown and save the header level.
			chunk.findTags(/#+[ ]*/, /[ ]*#+/);
			if(/#+/.test(chunk.startTag)){
				headerLevel = re.lastMatch.length;
			}
			chunk.startTag = chunk.endTag = "";
			
			// Try to get the current header level by looking for - and = in the line
			// below the selection.
			chunk.findTags(null, /\s?(-+|=+)/);
			if(/=+/.test(chunk.endTag)){
				headerLevel = 1;
			}
			if(/-+/.test(chunk.endTag)){
				headerLevel = 2;
			}
			
			// Skip to the next line so we can create the header markdown.
			chunk.startTag = chunk.endTag = "";
			chunk.addBlankLines(1, 1);

			// We make a level 2 header if there is no current header.
			// If there is a header level, we substract one from the header level.
			// If it's already a level 1 header, it's removed.
			var headerLevelToCreate = headerLevel == 0 ? 2 : headerLevel - 1;
			if(headerLevelToCreate > 0){
				// The button only creates level 1 and 2 underline headers.
				// Why not have it iterate over hash header levels?  Wouldn't that be easier and cleaner?
				var headerChar = headerLevelToCreate >= 2 ? "-" : "=";
				var len = chunk.selection.length;
				if(len > mooWMD.Config.lineLength){
					len = mooWMD.Config.lineLength;
				}
				chunk.endTag = "\n";
				while(len--){
					chunk.endTag += headerChar;
				}
			}
		},//EOF mooWMD.SpritedButtonRow.doHeading

		/**
		 * 
		 */
		doHorizontalRule: function(chunk, postProcessing, useDefaultText){
			chunk.startTag = "----------\n";
			chunk.selection = "";
			chunk.addBlankLines(2, 1, true);
		},//EOF mooWMD.SpritedButtonRow.doHorizontalRule

		/**
		 * 
		 */
		doList: function(chunk, postProcessing, isNumberedList, useDefaultText){
			// These are identical except at the very beginning and end.
			// Should probably use the regex extension function to make this clearer.
			var previousItemsRegex = /(\n|^)(([ ]{0,3}([*+-]|\d+[.])[ \t]+.*)(\n.+|\n{2,}([*+-].*|\d+[.])[ \t]+.*|\n{2,}[ \t]+\S.*)*)\n*$/;
			var nextItemsRegex = /^\n*(([ ]{0,3}([*+-]|\d+[.])[ \t]+.*)(\n.+|\n{2,}([*+-].*|\d+[.])[ \t]+.*|\n{2,}[ \t]+\S.*)*)\n*/;
			
			// The default bullet is a dash but others are possible.
			// This has nothing to do with the particular HTML bullet,
			// it's just a markdown bullet.
			var bullet = "-";
			
			// The number in a numbered list.
			var num = 1;
			
			// Get the item prefix - e.g. " 1. " for a numbered list, " - " for a bulleted list.
			var getItemPrefix = function(){
				var prefix;
				if(isNumberedList){
					prefix = " " + num + ". ";
					num++;
				}
				else{
					prefix = " " + bullet + " ";
				}
				return prefix;
			};
			
			// Fixes the prefixes of the other list items.
			var getPrefixedItem = function(itemText){
			
				// The numbering flag is unset when called by autoindent.
				if(isNumberedList === undefined){
					isNumberedList = /^\s*\d/.test(itemText);
				}
				
				// Renumber/bullet the list element.
				itemText = itemText.replace(/^[ ]{0,3}([*+-]|\d+[.])\s/gm,
					function( _ ){
						return getItemPrefix();
					});
					
				return itemText;
			};
			
			chunk.findTags(/(\n|^)*[ ]{0,3}([*+-]|\d+[.])\s+/, null);
			
			if(chunk.before && !/\n$/.test(chunk.before) && !/^\n/.test(chunk.startTag)){
				chunk.before += chunk.startTag;
				chunk.startTag = "";
			}
			
			if(chunk.startTag){
				
				var hasDigits = /\d+[.]/.test(chunk.startTag);
				chunk.startTag = "";
				chunk.selection = chunk.selection.replace(/\n[ ]{4}/g, "\n");
				chunk.unwrap();
				chunk.addBlankLines();
				
				if(hasDigits){
					// Have to renumber the bullet points if this is a numbered list.
					chunk.after = chunk.after.replace(nextItemsRegex, getPrefixedItem);
				}
				if(isNumberedList == hasDigits){
					return;
				}
			}
			var nLinesBefore = 1;
			chunk.before = chunk.before.replace(previousItemsRegex,
				function(itemText){
					if(/^\s*([*+-])/.test(itemText)){
						bullet = RegExp.$1;
					}
					nLinesBefore = /[^\n]\n\n[^\n]/.test(itemText) ? 1 : 0;
					return getPrefixedItem(itemText);
				});
				
			if(!chunk.selection){
				chunk.selection = useDefaultText ? "List item" : " ";
			}
			var prefix = getItemPrefix();
			var nLinesAfter = 1;
			chunk.after = chunk.after.replace(nextItemsRegex,
				function(itemText){
					nLinesAfter = /[^\n]\n\n[^\n]/.test(itemText) ? 1 : 0;
					return getPrefixedItem(itemText);
				});
				
			chunk.trimWhitespace(true);
			chunk.addBlankLines(nLinesBefore, nLinesAfter, true);
			chunk.startTag = prefix;
			var spaces = prefix.replace(/./g, " ");
			chunk.wrap(mooWMD.Config.lineLength - spaces.length);
			chunk.selection = chunk.selection.replace(/\n/g, "\n" + spaces);
		},//EOF mooWMD.SpritedButtonRow.doList
	
		/**
		 *Moves the cursor to the next line and continues lists, quotes and code.
		 */
		doAutoindent: function(chunk, postProcessing, useDefaultText){
			chunk.before = chunk.before.replace(/(\n|^)[ ]{0,3}([*+-]|\d+[.])[ \t]*\n$/, "\n\n");
			chunk.before = chunk.before.replace(/(\n|^)[ ]{0,3}>[ \t]*\n$/, "\n\n");
			chunk.before = chunk.before.replace(/(\n|^)[ \t]+\n$/, "\n\n");
			useDefaultText = false;
			
			if(/(\n|^)[ ]{0,3}([*+-])[ \t]+.*\n$/.test(chunk.before)){
				if(this.doList){
					this.doList(chunk, postProcessing, false, true);
				}
			}
			if(/(\n|^)[ ]{0,3}(\d+[.])[ \t]+.*\n$/.test(chunk.before)){
				if(this.doList){
					this.doList(chunk, postProcessing, true, true);
				}
			}
			if(/(\n|^)[ ]{0,3}>[ \t]+.*\n$/.test(chunk.before)){
				if(this.doBlockquote){
					this.doBlockquote(chunk, postProcessing, useDefaultText);
				}
			}
			if(/(\n|^)(\t|[ ]{4,}).*\n$/.test(chunk.before)){
				if(this.doCode){
					this.doCode(chunk, postProcessing, useDefaultText);
				}
			}
		},//EOF mooWMD.SpritedButtonRow.doAutoindent





		/**
		 * 
		 */
		setUndoRedoButtonStates:function(){
			if(this.undoMgr){
				this.setupButton($("wmd-undo-button"+this.postfix), this.undoMgr.canUndo());
				this.setupButton($("wmd-redo-button"+this.postfix), this.undoMgr.canRedo());
			}
		},

		/**
		 * 
		 */
		setupButton: function(button, isEnabled) {
		
			var normalYShift = "0px";
			var disabledYShift = "-20px";
			var highlightYShift = "-40px";
			
			if(isEnabled) {
				button.style.backgroundPosition = button.XShift + " " + normalYShift;
				button.onmouseover = function(){
					this.style.backgroundPosition = this.XShift + " " + highlightYShift;
				};
							
				button.onmouseout = function(){
					this.style.backgroundPosition = this.XShift + " " + normalYShift;
				};
				
	// Internet explorer has problems with CSS sprite buttons that use HTML
	// lists.  When you click on the background image "button", IE will 
	// select the non-existent link text and discard the selection in the
	// textarea.  The solution to this is to cache the textarea selection
	// on the button's mousedown event and set a flag.  In the part of the
	// code where we need to grab the selection, we check for the flag
	// and, if it's set, use the cached area instead of querying the
	// textarea.
	//
	// This ONLY affects Internet Explorer (tested on versions 6, 7
	// and 8) and ONLY on button clicks.  Keyboard shortcuts work
	// normally since the focus never leaves the textarea.
				if(Browser.Engine.trident) {
					button.onmousedown =  function() {
						this.input.set('ieRetardedClick',true);
						this.input.set('ieCachedRange',document.selection.createRange()); 
					};
				}
				
				if (!button.isHelp){
					button.addEvent('click',function(E) {
															var Button=$(E.target);
															if (Button.onmouseout) {
																Button.onmouseout();
															}
															this.doClick(Button);
															return false;
														}.bind(this)
									);
				}
			}
			else {
				button.style.backgroundPosition = button.XShift + " " + disabledYShift;
				button.onmouseover = button.onmouseout = button.onclick = function(){};
			}
		},//EOF mooWMD.SpritedButtonRow.setupButton

		/**
		 * Perform the button's action.
		 */
		doClick$: function(button){
			return this.doClick($(button+this.postfix));
		},
		doClick: function(button){
			this.input.focus();
			
			if (button.textOp) {
				
				if (this.undoMgr) {
					this.undoMgr.setCommandMode();
				}
				
				var state = new mooWMD.TextareaState(this.input);
				
				if (!state) {
					return;
				}
				
				var chunks = state.getChunks();
				
				// Some commands launch a "modal" prompt dialog.  Javascript
				// can't really make a modal dialog box and the WMD code
				// will continue to execute while the dialog is displayed.
				// This prevents the dialog pattern I'm used to and means
				// I can't do something like this:
				//
				// var link = CreateLinkDialog();
				// makeMarkdownLink(link);
				// 
				// Instead of this straightforward method of handling a
				// dialog I have to pass any code which would execute
				// after the dialog is dismissed (e.g. link creation)
				// in a function parameter.
				//
				// Yes this is awkward and I think it sucks, but there's
				// no real workaround.  Only the image and link code
				// create dialogs and require the function pointers.
				var fixupInputArea = function(){
				
					this.input.focus();
					
					if (chunks) {
						state.setChunks(chunks);
					}
					
					state.restore();
					this.previewRefreshCallback();
				}.bind(this);
				
				var useDefaultText = true;
				var noCleanup = button.textOp(chunks, fixupInputArea, useDefaultText);
				
				if(!noCleanup) {
					fixupInputArea();
				}
				
			}
			
			if (button.execute) {
				button.execute();
			}
		},//EOF mooWMD.SpritedButtonRow.doClick
		
		/**
		 * Adds button short cuts to the listbox (Event)
		 */
		addButtonActionsToInputBox: function(E){
			// Check to see if we have a button key and, if so execute the callback.
			if (E.control || E.meta) {
		
				var keyCodeStr = String.fromCharCode(E.code).toLowerCase();
				switch(keyCodeStr) {
					case "b":
						this.doClick($("wmd-bold-button"+this.postfix));
						break;
					case "i":
						this.doClick($("wmd-italic-button"+this.postfix));
						break;
					case "l":
						this.doClick($("wmd-link-button"+this.postfix));
						break;
					case "q":
						this.doClick($("wmd-quote-button"+this.postfix));
						break;
					case "k":
						this.doClick($("wmd-code-button"+this.postfix));
						break;
					case "g":
						this.doClick($("wmd-image-button"+this.postfix));
						break;
					case "o":
						this.doClick($("wmd-olist-button"+this.postfix));
						break;
					case "u":
						this.doClick($("wmd-ulist-button"+this.postfix));
						break;
					case "h":
						this.doClick($("wmd-heading-button"+this.postfix));
						break;
					case "r":
						this.doClick($("wmd-hr-button"+this.postfix));
						break;
					case "y":
						this.doClick($("wmd-redo-button"+this.postfix));
						break;
					case "z":
						if(E.shift) {
							this.doClick($("wmd-redo-button"+this.postfix));
						}else{
							this.doClick($("wmd-undo-button"+this.postfix));
						}
						break;
					default:
						return;
				}//eof SWITCH
				E.stop();					
			}//eof IF					
		}//EOF EOF mooWMD.SpritedButtonRow.addButtonActionsToInputBox


	}),//EOF mooWMD.SpritedButtonRow
	
	/**
	 * This simulates a modal dialog box and asks for the URL when you
	 * click the hyperlink or image buttons.
	 * 
	 * text: The html for the input box.
	 * defaultInputText: The default value that appears in the input box.
	 * makeLinkMarkdown: The function which is executed when the prompt is dismissed, either via OK or Cancel
	 */
	Prompt: new Class({
		// These variables need to be declared at this level since they are used
		// in multiple functions.
		dialog: null,			// The dialog box.
		background: null,		// The background beind the dialog box.
		input: null,			// The text box where you enter the hyperlink.
		makeLinkMarkDown: null, //The function which is executed when the prompt is dismissed, either via OK or Cancel
		defaultInputText:'',
		text: '',
		chunk: null,
		isImage: false,
		postProcessing: null, //Delegate for the callback when prompt is dismissed
		
		initialize:function(chunk,postProcessing,isImage){
			this.isImage=isImage;
			if(this.isImage){
				this.text=mooWMD.Config.imageDialogText;
				this.defaultInputText = mooWMD.Config.imageDefaultText;
			}else{
				this.text=mooWMD.Config.linkDialogText;
				this.defaultInputText = mooWMD.Config.linkDefaultText;
			}
			this.chunk=chunk;
			this.postProcessing=postProcessing;
		},//EOF initialize
		
		doLinkOrImage: function(){
			this.chunk.trimWhitespace();
			this.chunk.findTags(/\s*!?\[/, /\][ ]?(?:\n[ ]*)?(\[.*?\])?/);
			
			if (this.chunk.endTag.length > 1) {
			
				this.chunk.startTag = this.chunk.startTag.replace(/!?\[/, "");
				this.chunk.endTag = "";
				this.addLinkDef(this.chunk, null);
			}
			else {
				if (/\n\n/.test(this.chunk.selection)) {
					this.addLinkDef(this.chunk, null);
					return;
				}
				this.build();
				return true;
			}//EOF else
		},//EOF Prompt.doLinkOrImage
		
		/**
		 * Procedural code break
		 */
		build: function(){
			this.createBackground();
			/*
			// Why is this in a zero-length timeout?
			// Is it working around a browser bug?
			top.setTimeout(function(){
			*/
			this.createDialog();
			var defTextLen = this.defaultInputText.length;
			if (this.input.selectionStart !== undefined) {
				this.input.selectionStart = 0;
				this.input.selectionEnd = defTextLen;
			}
			else if (this.input.createTextRange) {
				var range = this.input.createTextRange();
				range.collapse(false);
				range.moveStart("character", -defTextLen);
				range.moveEnd("character", defTextLen);
				range.select();
			}
			
			this.input.focus();
			/*
			}.bind(this), 0);
			*/
		},//EOF Prompt.build
	
		/**
		 *  Used as a keydown event handler. Esc dismisses the prompt.
		 * Key code 27 is ESC.
		 */
		checkEscape: function(E){
			if (E.code === 27) {
				this.close(true);
			}
		},
		
		/**
		 * Dismisses the hyperlink input box.
		 * isCancel is true if we don't care about the input text.
		 * isCancel is false if we are going to keep the text.
		 */
		close: function(isCancel){
			document.body.removeEvent("keydown", this.checkEscape);
			var text = this.input.value;

			if (isCancel){
				text = null;
			}else{
				// Fixes common pasting errors.
				text = text.replace('http://http://', 'http://');
				text = text.replace('http://https://', 'https://');
				text = text.replace('http://ftp://', 'ftp://');
				
				if (text.indexOf('http://') === -1 && text.indexOf('ftp://') === -1 && text.indexOf('https://') === -1) {
					text = 'http://' + text;
				}
			}
			
			this.dialog.destroy();
			this.background.destroy();
			this.makeLinkMarkdown(text);
			return false;
		},//EOF Prompt.close
		
		/**
		 * Creates the background behind the hyperlink text entry box.
		 * Most of this has been moved to CSS but the div creation and
		 * browser-specific hacks remain here.
		 */
		createBackground: function(){
			this.background = new Element("div");
			this.background.className = "wmd-prompt-background";
			
			this.background.setStyles({
								'position':'absolute',
								'top':0,
								'zIndex':1000
								});
			
			// Some versions of Konqueror don't support transparent colors
			// so we make the whole window transparent.
			//
			// Is this necessary on modern konqueror browsers?
			if (Browser.Engine.webkit){
				this.background.style.backgroundColor = "transparent";
			}
			else if (Browser.Engine.trident){
				this.background.style.filter = "alpha(opacity=50)";
			}
			else {
				this.background.style.opacity = "0.5";
			}
			
			//TODO fill those values
			//var pageSize = position.getPageSize();
			//this.background.style.height = pageSize[1] + "px";
			
			if(Browser.Engine.trident ){
				this.background.style.left = doc.documentElement.scrollLeft;
				this.background.style.width = doc.documentElement.clientWidth;
			}
			else {
				this.background.style.left = "0";
				this.background.style.width = "100%";
			}
			
			$(document.body).adopt(this.background);
		},//EOF Prompt.createBackground
		
		/**
		 * Create the text input box form/window.
		 */
		createDialog: function(){

			// The main dialog box.
			this.dialog = new Element("div");
			this.dialog.className = "wmd-prompt-dialog";
			this.dialog.setStyles({
									'padding':"10px;",
									'position':"fixed",
									'width':"400px",
									'zIndex':"1001"
									});

			// The dialog text.
			var question = new Element("div");
			question.innerHTML = this.text;
			question.style.padding = "5px";
			this.dialog.adopt(question);
			
			//TODO: mooWMD WATCH OUT !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
			// The web form container for the text box and buttons.

			var form = new Element("form");
			form.addEvent('submit',function(){ return this.close(false); }.bind(this));
			form.setStyles({
							'padding':0,
							'margin':0,
							'float':'left',
							'width':'100%',
							'textAlign':'center',
							'position':'relative'
							});
			this.dialog.adopt(form);
			
			// The input text box
			this.input = new Element("input",{
					value:this.defaultInputText,
					type:'text'
				});
			this.input.setStyles({
							'display':'block',
							'width':'80%',
							'marginLeft':'auto',
							'marginRight':'auto'
							});
			form.adopt(this.input);
		
			// The ok button
			var okButton = new Element("input",{
											type:'button',
											value:'OK'
											});
			okButton.addEvent('click',function(){ return this.close(false) }.bind(this));
			okButton.setStyles({
							'margin':"10px",
							'display':"inline",
							'width':"7em"
						});

			// The cancel button
			var cancelButton = new Element("input",{
											type:'button',
											value:'Cancel'
											});
			cancelButton.addEvent('click',function(){ return this.close(true) }.bind(this));
			cancelButton.setStyles({
							'margin':"10px",
							'display':"inline",
							'width':"7em"
						});

			// The order of these buttons is different on macs.
			if (Browser.Platform.mac) {
				form.adopt(cancelButton);
				form.adopt(okButton);
			}
			else {
				form.adopt(okButton);
				form.adopt(cancelButton);
			}

			$(document.body).addEvent("keydown", this.checkEscape);
			this.dialog.style.top = "50%";
			this.dialog.style.left = "50%";
			this.dialog.style.display = "block";
			document.body.adopt(this.dialog);
			
			// This has to be done AFTER adding the dialog to the form if you
			// want it to be centered.
			this.dialog.style.marginTop = -(this.dialog.getSize().y / 2) + "px";
			this.dialog.style.marginLeft = -(this.dialog.getSize().x / 2) + "px";
		},//EOF Prompt.createDialog
		
		/**
		 * The function to be executed when you enter a link and press OK or Cancel.
		 * Marks up the link and adds the ref.
		 */
		makeLinkMarkdown: function(link){
			if (link !== null) {
				this.chunk.startTag = this.chunk.endTag = "";
				var linkDef = " [999]: " + link;
				var num = this.addLinkDef(this.chunk, linkDef);
				this.chunk.startTag = this.isImage ? "![" : "[";
				this.chunk.endTag = "][" + num + "]";
				if (!this.chunk.selection) {
					if (this.isImage) {
						this.chunk.selection = "alt text";
					}else {
						this.chunk.selection = "link text";
					}
				}
			}
			this.postProcessing();
		},//EOF Prompt.makeLinkMarkdown
		addLinkDef: function(chunk, linkDef){
			var refNumber = 0; // The current reference number
			var defsToAdd = {}; //
			// Start with a clean slate by removing all previous link definitions.
			this.chunk.before = this.stripLinkDefs(this.chunk.before, defsToAdd);
			this.chunk.selection = this.stripLinkDefs(this.chunk.selection, defsToAdd);
			this.chunk.after = this.stripLinkDefs(this.chunk.after, defsToAdd);
			
			var defs = "";
			var regex = /(\[(?:\[[^\]]*\]|[^\[\]])*\][ ]?(?:\n[ ]*)?\[)(\d+)(\])/g;
			
			var addDefNumber = function(def){
				refNumber++;
				def = def.replace(/^[ ]{0,3}\[(\d+)\]:/, "  [" + refNumber + "]:");
				defs += "\n" + def;
			};
			
			var getLink = function(wholeMatch, link, id, end){
				if (defsToAdd[id]) {
					addDefNumber(defsToAdd[id]);
					return link + refNumber + end;
					
				}
				return wholeMatch;
			};
			
			this.chunk.before = this.chunk.before.replace(regex, getLink);
			
			if (linkDef) {
				addDefNumber(linkDef);
			}
			else {
				this.chunk.selection = this.chunk.selection.replace(regex, getLink);
			}
			
			var refOut = refNumber;
			this.chunk.after = this.chunk.after.replace(regex, getLink);
			
			if (this.chunk.after) {
				this.chunk.after = this.chunk.after.replace(/\n*$/, "");
			}
			if (!this.chunk.after) {
				this.chunk.selection = this.chunk.selection.replace(/\n*$/, "");
			}
			this.chunk.after += "\n\n" + defs;
			return refOut;
		},//EOF Prompt.addLinkDef
		
		/**
		 * 
		 */
		stripLinkDefs: function(text, defsToAdd){
			text = text.replace(/^[ ]{0,3}\[(\d+)\]:[ \t]*\n?[ \t]*<?(\S+?)>?[ \t]*\n?[ \t]*(?:(\n*)["(](.+?)[")][ \t]*)?(?:\n+|$)/gm, 
			function(totalMatch, id, link, newlines, title){	
				defsToAdd[id] = totalMatch.replace(/\s*$/, "");
				if (newlines) {
					// Strip the title and return that separately.
					defsToAdd[id] = totalMatch.replace(/["(](.+?)[")]$/, "");
					return newlines + title;
				}
				return "";
			});
			return text;
		}//EOF Prompt.stripLinkDefs
	}),//EOF mooWMD.Prompt
	
	UndoManager:new Class({
		undoStack: [], // A stack of undo states
		stackPtr: 0, // The index of the current state
		mode: "none",
		lastState: null, // The last state
		poller: null,
		timer: null, // The setTimeout handle for cancelling the timer
		inputStateObj: null,
		undoCallback: null,
		input: null,//the text area		
		
		initialize: function(undoCallback,input){
			this.undoCallback=undoCallback;
			this.input=input;
			this.poller = new mooWMD.InputPoller(this.handlePaste.bind(this), mooWMD.Config.pastePollInterval,this.input);
			
			//add events
			this.input.addEvent("keypress", function(E){
				// key Code 89: y
				// key Code 90: z
				if ((E.control || E.meta) && (E.code == 89 || E.code == 90)) {
					E.stop();
				}
			});
			
			this.input.addEvent("keydown", this.handleCtrlYZ.bind(this));
			this.input.addEvent("keydown", this.handleModeChange.bind(this));
			this.input.addEvent( "mousedown", function(){
				this.setMode("moving");
			}.bind(this));
			this.input.onpaste = this.handlePaste.bind(this);
			this.input.ondrop = this.handlePaste.bind(this);

			//start
			this.refreshState();
			this.saveState();
		},//EOF mooWMD.UndoManager.initialize
		
		/**
		 * Set the mode for later logic steps.
		 */
		setMode: function(newMode, noSave){
			if (this.mode != newMode) {
				this.mode = newMode;
				if (!noSave) {
					this.saveState();
				}
			}
			if (!Browser.Engine.trident || this.mode != "moving") {
				this.timer = window.setTimeout(this.refreshState.bind(this), 1);
			}else {
				this.inputStateObj = null;
			}
		},//EOF mooWMD.UndoManager.setMode
		
		/**
		 * 
		 */		
		refreshState: function(){
			this.inputStateObj = new mooWMD.TextareaState(this.input);
			this.poller.tick();
			this.timer = undefined;
		},//EOF mooWMD.UndoManager.refreshState
		
		/**
		 * 
		 */
		setCommandMode: function(){
			this.mode = "command";
			this.saveState();
			this.timer = window.setTimeout(this.refreshState.bind(this), 0); //I HAVE NO IDEA WHY THE TIME OUT
		},//EOF mooWMD.UndoManager.setCommandMode
		
		/**
		 * 
		 */		
		canUndo: function(){
			return this.stackPtr > 1;
		},//EOF mooWMD.UndoManager.canUndo
		
		/**
		 * 
		 */
		canRedo: function(){
			if (this.undoStack[this.stackPtr + 1]) {
				return true;
			}
			return false;
		},//EOF mooWMD.UndoManager.canRedo
		
		/**
		 * Removes the last state and restores it.
		 */
		undo: function(){
			if (this.canUndo()) {
				if (this.lastState) {
					// What about setting state -1 to null or checking for undefined?
					this.lastState.restore();
					this.lastState = null;
				}else {
					this.undoStack[this.stackPtr] = new mooWMD.TextareaState(this.input);
					this.undoStack[--this.stackPtr].restore();
					if (this.undoCallback) {
						this.undoCallback();
					}
				}
			}
			
			this.mode = "none";
			this.input.focus();
			this.refreshState();
		},//EOF mooWMD.UndoManager.undo
		
		/**
		 * 
		 */
		redo: function(){
			if (this.canRedo()) {
				this.undoStack[++this.stackPtr].restore();
				if (this.undoCallback) {
					this.undoCallback();
				}
			}
			this.mode = "none";
			this.input.focus();
			this.refreshState();
		},//EOF mooWMD.UndoManager.undo

		/**
		 * Push the input area state to the stack.
		 */
		saveState: function(){
			var currState = this.inputStateObj || new mooWMD.TextareaState(this.input);
			
			if (!currState) {
				return false;
			}
			if (this.mode == "moving") {
				if (!this.lastState) {
					this.lastState = currState;
				}
				return;
			}
			if (this.lastState) {
				if (this.undoStack[this.stackPtr - 1].text != this.lastState.text) {
					this.undoStack[this.stackPtr++] = this.lastState;
				}
				this.lastState = null;
			}
			this.undoStack[this.stackPtr++] = currState;
			this.undoStack[this.stackPtr + 1] = null;
			if (this.undoCallback) {
				this.undoCallback();
			}
		},//EOF mooWMD.UndoManager.saveState

		destroy: function(){
			if (this.poller) {
				this.poller.destroy();
			}
		},//EOF mooWMD.UndoManager.destroy

		//-------------- EVENTS -----------------
		
		/**
		 * 
		 */
		handleCtrlYZ: function(E){
			var handled = false;
			if (E.control || E.meta) {
				var keyCodeChar = String.fromCharCode(E.code);
				switch (keyCodeChar) {
					case "y":
						this.redo();
						E.stop();
						break;
						
					case "z":
						if (!E.shift) {
							this.undo();
						}
						else {
							this.redo();
						}
						E.stop();
						break;
				}
			}
		},//EOF mooWMD.UndoManager.handleCtrlYZ
		
		/**
		 * Set the mode depending on what is going on in the input area.
		 */
		handleModeChange: function(E){
			if (!E.control && !E.meta) {
				if ((E.code >= 33 && E.code <= 40) || (E.code >= 63232 && E.code <= 63235)) {
					// 33 - 40: page up/dn and arrow keys
					// 63232 - 63235: page up/dn and arrow keys on safari
					this.setMode("moving");
				}else if (E.code == 8 || E.code == 46 || E.code == 127) {
					// 8: backspace
					// 46: delete
					// 127: delete
					this.setMode("deleting");
				}else if (E.code == 13) {
					// 13: Enter
					this.setMode("newlines");
				}else if (E.code == 27) {
					// 27: escape
					this.setMode("escape");
				}else if ((E.code < 16 || E.code > 20) && E.code != 91) {
					// 16-20 are shift, etc. 
					// 91: left window key
					// I think this might be a little messed up since there are
					// a lot of nonprinting keys above 20.
					this.setMode("typing");
				}
			}
		},//EOF mooWMD.UndoManager.handleModeChange

		handlePaste: function(E){
			if (Browser.Engine.trident || (this.inputStateObj && this.inputStateObj.text != this.input.value)) {
				if (this.timer == undefined) {
					this.mode = "paste";
					this.saveState();
					this.refreshState();
				}
			}
		}//EOF mooWMD.UndoManager.handlePaste
	}),//EOF mooWMD.UndoManager
	
	/**
	 * The input textarea state/contents.
	 * This is used to implement undo/redo by the undo manager.
	 */
	TextareaState: new Class({
		input: null,
		start: '',
		end: '',
		scrollTop: 0,
		text: '',
		
		initialize: function(input){
			this.input=input;
			if (!mooWMD.Utils.isVisible(this.input)) {
				return;
			}
			this.setInputAreaSelectionStartEnd();
			this.scrollTop = this.input.scrollTop;
			if (!this.text && this.input.selectionStart || this.input.selectionStart === 0) {
				this.text = this.input.value;
			}
		},//EOF mooWMD.TextareaState.initialize
	
		/**
		 * Sets the selected text in the input box after we've performed an
		 * operation.
		 */
		setInputAreaSelection: function(){		
			if (!mooWMD.Utils.isVisible(this.input)) {
				return;
			}
			
			if (this.input.selectionStart !== undefined && !Browser.Engine.presto) {
				this.input.focus();
				this.input.selectionStart = this.start;
				this.input.selectionEnd = this.end;
				this.input.scrollTop = this.scrollTop;
			}else if (document.selection) {
				if (document.activeElement && document.activeElement !== this.input) {
					return;
				}
				this.input.focus();
				var range = this.input.createTextRange();
				range.moveStart("character", -this.input.value.length);
				range.moveEnd("character", -this.input.value.length);
				range.moveEnd("character", this.end);
				range.moveStart("character", this.start);
				range.select();
			}
		},//EOF mooWMD.TextareaState.setInputAreaSelection
		
		/**
		 * 
		 */
		setInputAreaSelectionStartEnd: function(){
			if (this.input.selectionStart || this.input.selectionStart === 0) {
				this.start = this.input.selectionStart;
				this.end = this.input.selectionEnd;
			}else if (document.selection) {
				this.text = mooWMD.Utils.fixEolChars(this.input.value);
				
	// Internet explorer has problems with CSS sprite buttons that use HTML
	// lists.  When you click on the background image "button", IE will 
	// select the non-existent link text and discard the selection in the
	// textarea.  The solution to this is to cache the textarea selection
	// on the button's mousedown event and set a flag.  In the part of the
	// code where we need to grab the selection, we check for the flag
	// and, if it's set, use the cached area instead of querying the
	// textarea.
	//
	// This ONLY affects Internet Explorer (tested on versions 6, 7
	// and 8) and ONLY on button clicks.  Keyboard shortcuts work
	// normally since the focus never leaves the textarea.
				var range;
				if(this.input.get('ieRetardedClick') && this.input.get('ieCachedRange')) {
					range = this.input.get('ieCachedRange');
					this.input.set('ieRetardedClick',false);
				}else {
					range = document.selection.createRange();
				}
				var fixedRange = mooWMD.Utils.fixEolChars(range.text);
				var marker = "\x07";
				var markedRange = marker + fixedRange + marker;
				range.text = markedRange;
				var inputText = mooWMD.Utils.fixEolChars(this.input.value);
				range.moveStart("character", -markedRange.length);
				range.text = fixedRange;
				this.start = inputText.indexOf(marker);
				this.end = inputText.lastIndexOf(marker) - marker.length;
				var len = this.text.length - mooWMD.Utils.fixEolChars(this.input.value).length;
				if (len) {
					range.moveStart("character", -fixedRange.length);
					while (len--) {
						fixedRange += "\n";
						this.end += 1;
					}
					range.text = fixedRange;
				}					
				this.setInputAreaSelection();
			}
		},//EOF mooWMD.TextareaState.setInputAreaSelection

		/**
		 * Restore this state into the input area.
		 */
		restore: function(){
			if (this.text != undefined && this.text != this.input.value) {
				this.input.value = this.text;
			}
			this.setInputAreaSelection();
			this.input.scrollTop = this.scrollTop;
		},//EOF mooWMD.TextareaState.restore
		
		/**
		 * Gets a collection of HTML chunks from the input textarea.
		 */
		getChunks: function(){
 			return new mooWMD.Chunk(this);
		},//EOF mooWMD.TextareaState.getChunks
		
		/**
		 * Sets the TextareaState properties given a chunk of markdown.
		 */
		setChunks: function(chunk){
			chunk.before = chunk.before + chunk.startTag;
			chunk.after = chunk.endTag + chunk.after;
			if (Browser.Engine.presto) {
				chunk.before = chunk.before.replace(/\n/g, "\r\n");
				chunk.selection = chunk.selection.replace(/\n/g, "\r\n");
				chunk.after = chunk.after.replace(/\n/g, "\r\n");
			}
			this.start = chunk.before.length;
			this.end = chunk.before.length + chunk.selection.length;
			this.text = chunk.before + chunk.selection + chunk.after;
			this.scrollTop = chunk.scrollTop;
		}//EOF mooWMD.TextareaState.setChunks

	}),//EOF mooWMD.TextareaState setInputAreaSelectionStartEnd
	
	/**
	 * Listener, stores the changes hapenning on the textarea
	 */
	InputPoller: new Class({
		callback: null,
		interval: 100,
		input: null,

		// Stored start, end and text.  Used to see if there are changes to the input.
		lastStart: '',
		lastEnd: '',
		markdown: '',
		
		// Used to cancel monitoring on destruction.
		killHandle: null,
		
		initialize: function(callback, interval,input){
			this.callback=callback;
			this.interval=interval;
			this.input=input;
			this.assignInterval();				
		},//EOF mooWMD.InputPoller.initialize
		
		/**
		 * 
		 */
		tick: function(){
			if (!mooWMD.Utils.isVisible(this.input)) {
				return;
			}
			
			// Update the selection start and end, text.
			if (this.input.selectionStart || this.input.selectionStart === 0) {
				var start = this.input.selectionStart;
				var end = this.input.selectionEnd;
				if (start != this.lastStart || end != this.lastEnd) {
					this.lastStart = start;
					this.lastEnd = end;
					
					if (this.markdown != this.input.value) {
						this.markdown = this.input.value;
						return true;
					}
				}
			}
			return false;
		},//EOF mooWMD.InputPoller.tick
		
		/**
		 * 
		 */
		doTickCallback: function(){
			if (!mooWMD.Utils.isVisible(this.input)) {
				return;
			}
			
			// If anything has changed, call the function.
			if (this.tick()) {
				this.callback();
			}
		},//EOF mooWMD.InputPoller.doTickCallback
		
		/**
		 * Set how often we poll the textarea for changes.
		 */
		assignInterval: function(){
			this.killHandle = window.setInterval(this.doTickCallback.bind(this), this.interval);
		},//EOF mooWMD.InputPoller.assignInterval

		/**
		 * 
		 */
		destroy: function(){
			window.clearInterval(this.killHandle);
		}//EOF mooWMD.InputPoller.destroy
		
	}),//EOF mooWMD.InputPoller

	/**
	 * 
	 */
	Editor: new Class({
		input: null,
		UndoMgr: null,
		Buttons: null,
		
		initialize: function(input,previewRefreshCallback,postfix){
			this.input=input;
			this.Buttons=new mooWMD.SpritedButtonRow(postfix,previewRefreshCallback,this.input,this);
			this.UndoMgr=new mooWMD.UndoManager(function(){
												previewRefreshCallback();
												this.Buttons.setUndoRedoButtonStates();
											}.bind(this),
											this.input);
			this.Buttons.undoMgr=this.UndoMgr;
			this.Buttons.build();
			
			//attach some events to the input
			this.input.addEvent("keyup",this.autoContinue.bind(this));
			// Disable ESC clearing the input textarea on IE
			if (Browser.Engine.trident) {
				this.input.addEvent("keydown",this.disableEsc);
			}
			this.prepareTextForSubmit();
		},//EOF mooWMD.Editor.initialize
		
		/**
		 * ----------------------------- input events
		 */
		
		/**
		 * Auto-continue lists, code blocks and block quotes when
		 * the enter key is pressed.
		 */
		autoContinue: function(E){
				if (!E.shift && !E.control && !E.meta) {
					if (E.code === 13) {
						var fakeButton = {};
						fakeButton.textOp = this.Buttons.doAutoindent.bind(this.Buttons);
						this.Buttons.doClick(fakeButton);
					}
				}
		},//EOF mooWMD.Editor.autoContinue

		/**
		 * Disable ESC clearing the input textarea on IE
		 */
		disableEsc: function(E){
			// Key code 27 is ESC
			if (E.code === 27) {
				E.stop();
				return false;
			}
		},//EOF mooWMD.Editor.disableEsc
		
		/**
		 * Handle trasformation to HTML if textarea is inside a FORM
		 */
		prepareTextForSubmit: function(){
			if (this.input.form) {
				this.input.form.addEvent('submit',this.convertToHtml.bind(this));
			}
		},//EOF mooWMD.Editor.prepareTextForSubmit
		
		/**
		 * Convert the contents of the input textarea to HTML in the output/preview panels.
		 */
		convertToHtml: function(){
			var markdownConverter = new Attacklab.showdown.converter();
			var text = this.input.value;
			
			if (!/markdown/.test(mooWMD.Config.output.toLowerCase())) {
				this.input.value = markdownConverter.makeHtml(text);
			}
			return true;			
		},//EOF mooWMD.Editor.convertToHtml
		
		/**
		 * 
		 */
		undo: function(){
			this.UndoMgr.undo();
		},
		redo: function(){
			this.UndoMgr.redo();
		},
		destroy: function(){
			this.UndoMgr.destroy();
			this.input.style.marginTop = "";
		}
	}),//EOF mooWMD.Editor
	
	/**
	 * 
	 */
	PreviewMgr: new Class({
		panel: null,
		poller: null,
		oldInputText: '',
		htmlOut: '',
		converter: null,
		timeout: null,
		elapsedTime: 0,
		maxDelay: 3000,
		startType: "delayed",
		isFirstTimeFilled: true,
		
		initialize: function(panel){
			this.panel=panel;
			this.setupEvents();
			this.makePreviewHtml();
			if (this.panel.preview) {
				this.panel.preview.scrollTop = 0;
			}
			if (this.panel.output) {
				this.panel.output.scrollTop = 0;
			}
		},//EOF mooWMD.PreviewMgr.initialize
		
		/**
		 * Adds event listeners to elements and creates the input poller.
		 */
		setupEvents: function(){
			var listener=this.applyTimeout.bind(this);
			this.panel.input.addEvent("input", listener);
			this.panel.input.onpaste = listener;
			this.panel.input.ondrop = listener;
			this.panel.input.addEvent("keypress", listener);
			this.panel.input.addEvent("keydown", listener);
			this.poller = new mooWMD.InputPoller(listener, mooWMD.previewPollInterval,this.panel.input);
		},//EOF mooWMD.PreviewMgr.setupEvents
		
		/**
		 * TODO: convert to mootools shortcuts AND KILL
		 */
		getDocScrollTop: function(){
			var result = 0;
			if (top.innerHeight) {
				result = top.pageYOffset;
			}else if (document.documentElement && document.documentElement.scrollTop) {
				result = document.documentElement.scrollTop;
			}else if (document.body) {
				result = document.body.scrollTop;
			}
			return result;
		},//EOF mooWMD.PreviewMgr.getDocScrollTop
		
		/**
		 * 
		 */
		makePreviewHtml: function(){
			// If there are no registered preview and output panels
			// there is nothing to do.
			if (!this.panel.preview && !this.panel.output) {
				return;
			}
			var text = this.panel.input.value;
			if (text && text == this.oldInputText) {
				return; // Input text hasn't changed.
			}else {
				this.oldInputText = text;
			}
			
			var prevTime = new Date().getTime();
			if (!this.converter && Attacklab.showdown) {
				this.converter = new Attacklab.showdown.converter();
			}			
			if (this.converter) {
				text = this.converter.makeHtml(text);
			}
			
			// Calculate the processing time of the HTML creation.
			// It's used as the delay time in the event listener.
			var currTime = new Date().getTime();
			this.elapsedTime = currTime - prevTime;
			
			this.pushPreviewHtml(text);
			this.htmlOut = text;
		},//EOF mooWMD.PreviewMgr.makePreviewHtml
		
		/**
		 * setTimeout is already used.  Used as an event listener.
		 */
		applyTimeout: function(){
			if (this.timeout) {
				window.clearTimeout(this.timeout);
				this.timeout = undefined;
			}
			if (this.startType !== "manual") {
				var delay = 0;
				if (this.startType === "delayed") {
					delay = this.elapsedTime;
				}
				if (delay > this.maxDelay) {
					delay = this.maxDelay;
				}
				this.timeout = window.setTimeout(this.makePreviewHtml.bind(this), delay);
			}
		},//EOF mooWMD.PreviewMgr.applyTimeout
		
		/**
		 * 
		 */
		getScaleFactor: function(panel){
			if (panel.scrollHeight <= panel.clientHeight) {
				return 1;
			}
			return panel.scrollTop / (panel.scrollHeight - panel.clientHeight);
		},//EOF mooWMD.PreviewMgr.getScaleFactor
		
		/**
		 *
		 */
		 setPanelScrollTops: function(){
			if (this.panel.preview) {
				this.panel.preview.scrollTop = (this.panel.preview.scrollHeight - this.panel.preview.clientHeight) * this.getScaleFactor(this.panel.preview);
			}
			if (this.panel.output) {
				this.panel.output.scrollTop = (this.panel.output.scrollHeight - this.panel.output.clientHeight) * this.getScaleFactor(this.panel.output);
				;
			}
		},//EOF mooWMD.PreviewMgr.setPanelScrollTops
		
		/**
		 * 
		 */
		refresh: function(requiresRefresh){
			if (requiresRefresh) {
				this.oldInputText = "";
				this.makePreviewHtml();
			}else {
				this.applyTimeout();
			}
		},//EOF mooWMD.PreviewMgr.refresh
		
		/**
		 * 
		 */
		processingTime: function(){
			return this.elapsedTime;
		},//EOF mooWMD.PreviewMgr.processingTime
		
		/**
		 * The output HTML
		 */
		output: function(){
			return this.htmlOut;
		},//EOF mooWMD.PreviewMgr.output
		
		/**
		 * The mode can be "manual" or "delayed"
		 */
		setUpdateMode: function(mode){
			this.startType = mode;
			this.refresh();
		},//EOF mooWMD.PreviewMgr.setUpdateMode
		
		/**
		 * 
		 */
		pushPreviewHtml: function(text){
			//var emptyTop = position.getTop(wmd.panels.input) - getDocScrollTop();
			var emptyTop = this.panel.input.getPosition().y - this.getDocScrollTop();
			
			// Send the encoded HTML to the output textarea/div.
			if (this.panel.output) {
				// The value property is only defined if the output is a textarea.
				if (this.panel.output.value !== undefined) {
					this.panel.output.value = text;
					this.panel.output.readOnly = true;
				}
				// Otherwise we are just replacing the text in a div.
				// Send the HTML wrapped in <pre><code>
				else {
					var newText = text.replace(/&/g, "&amp;");
					newText = newText.replace(/</g, "&lt;");
					this.panel.output.innerHTML = "<pre><code>" + newText + "</code></pre>";
				}
			}
			
			if (this.panel.preview) {
				this.panel.preview.innerHTML = text;
			}
			this.setPanelScrollTops();
			if (this.isFirstTimeFilled) {
				this.isFirstTimeFilled = false;
				return;
			}			
			var fullTop = this.panel.input.getPosition().y - this.getDocScrollTop();
			if (Browser.Engine.trident) {
				window.setTimeout(function(){
					window.scrollBy(0, fullTop - emptyTop);
				}, 0);
			}else {
				window.scrollBy(0, fullTop - emptyTop);
			}
		},//EOF mooWMD.PreviewMgr.pushPreviewHtml
		
		/**
		 * 
		 */
		destroy: function(){
			if (this.poller) {
				this.poller.destroy();
			}
		}//EOF mooWMD.PreviewMgr.destroy		
	}),//EOF mooWMD.PreviewMgr
	
	/**
	 * WMD - the method that attaches a WMD to each input textarea
	 */
	
	WMD: new Class({
		json: {},
		editors: [],//The editors (buttons + input + outputs) - the main object.
		previewMgrs: [],
		
		initialize: function(WmdJSON){
			this.json=WmdJSON;
		},
		
		/**
		 * Fired after the page has fully loaded.
		 */
		start: function(){
			var len=this.json.length;
			for(var i=0;i<len;i++){
				var preview=(this.json[i].preview || 'wmd-preview'+this.json[i].postfix);
				var output=(this.json[i].output || 'wmd-output'+this.json[i].postfix);
				var input=this.cleanP($(this.json[i].input));//A bug with Hebrew, I will NOT dive into showdown. It seems <p></p>tags are making
															 //a problem with hebrew. I will remove them.
				var postfix=this.json[i].postfix;
				var panel={
						preview: $(preview),
						output: $(output),
						input: input
				};
				var idx=this.previewMgrs.push(new mooWMD.PreviewMgr(panel));
				var previewRefreshCallback = this.previewMgrs[idx-1].refresh.bind(this.previewMgrs[idx-1]);
				this.editors.push(new mooWMD.Editor(input,previewRefreshCallback,postfix));
				this.previewMgrs[idx-1].refresh(true);
			}
		},
		/**
		 * A bug with Hebrew, I will NOT dive into showdown. It seems <p></p>tags are making
		 * a problem with hebrew. I will remove them.
		 */
		cleanP: function(input){
			var text=input.value;
			text=text.replace(/<p>/g,'');
			text=text.replace(/<\/p>/g,'\n');
			input.value=text;
			return input;
		}
	})//EOF mooWMD.WMD
}//EOF NAME SPACE <mooWMD namespace>

