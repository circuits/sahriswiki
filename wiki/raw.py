#!/usr/bin/env python

from circuits.web import Server, Controller 
from circuits import Debugger
from circuits.web import expose
from circuits import handler, Component
from circuits.web.errors import Forbidden

#log = open("log", "a")
#log.write(kwargs)
#log.close()

class ACL(Component):
	@handler("request", filter=True)
	def on_request(self, request, response):
		print request.remote.ip 

class Root(Controller):
	@expose("hi.html")
	def hi(self):
		fileHandle = open ( 'hi.html' )
		return """<script type="text/JavaScript"> 
<!--
function timedRefresh(timeoutPeriod) {
	setTimeout("location.reload(true);",timeoutPeriod);
}
//   -->
</script><body onload="JavaScript:timedRefresh(3000);">  %s""" % fileHandle.read()
		fileHandle.close()
	def index(self, *args, **kwargs):
		input = kwargs.get("input", None)
		print request.remote.ip
		if input != None:
			if len(input) > 0:
				fileHandle = open ( 'hi.html','w' )
				fileHandle.write(input)
				fileHandle.close()	

		return """<head> <script type="text/javascript">if(location.search) location.search = '';</script></head><body><iframe src="hi.html" height = "500" width = "1000"> </iframe>
<form name="input" action="" method="get"><textarea rows="4" cols="120" name="input">
</textarea>
<input type="submit" value="Write" />
</form></body>"""
	

(Server(("0.0.0.0", 8000)) + ACL() + Debugger(events=False, errors=True) + Root()).run() 



