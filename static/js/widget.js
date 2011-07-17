// Kwissle random question widget
// http://kwissle.com
//

var Kwissle = (function() {
  var _options = typeof kwissle_options != 'undefined' ? kwissle_options : {};
  var HOST_NAME = _options.host_name || 'kwissle.com'; // HARD CODED!
  var BASE_URL = ('https:' == document.location.protocol ? 'https://' : 'http://') + HOST_NAME;
  var CONTENT_URL = BASE_URL + '/widget/random/jsonp?callback=Kwissle.callback';
  var ROOT = _options.root_node_id || 'kwisslewidget';
  var ACTION_URL = BASE_URL + '/widget/answer/';
  var ROOT_CSS = _options.root_css || '';
  var CSS = '#' + ROOT + ' p{margin:2px}#' + ROOT + ' h3{margin:4px 2px}';

  function insertStylesheet() {
    var style = document.createElement('style');
    style.appendChild(document.createTextNode(CSS));
    document.getElementsByTagName('head')[0].appendChild(style);
  }
  function requestContent() {
    var s = document.createElement('script');
    s.type = 'text/javascript';
    s.defer = true;
    s.src = CONTENT_URL;
    document.getElementsByTagName('head')[0].appendChild(s);
  }
  document.write('<form action="' + ACTION_URL + '" method="post" id="' + ROOT + '" style="display:none"></form>');
  insertStylesheet();
  requestContent();
  return {
     callback: function(response) {
       if (!response) return;
       var div = document.getElementById(ROOT);
       var inv = document.createElement('input');
       inv.setAttribute('type', 'hidden');
       inv.setAttribute('value', response.id);
       inv.setAttribute('name', 'id');
       div.appendChild(inv);
       var h = document.createElement('h3');
       h.appendChild(document.createTextNode('Random '));
       var l = document.createElement('a');
       l.setAttribute('href', BASE_URL);
       addEvent(l, 'click', function(e) {
         window.open(this.href);
         e.preventDefault();
       });
       l.appendChild(document.createTextNode('Kwissle'));
       h.appendChild(l);
       h.appendChild(document.createTextNode(' question'));
       div.appendChild(h);
       var q = document.createElement('p');
       q.setAttribute('class', 'question');
       q.appendChild(document.createTextNode('Question: ' + response.text));
       div.appendChild(q);
       var a = document.createElement('div');
       var as = document.createElement('p');
       as.setAttribute('id', 'kwissle-answer');
       as.appendChild(document.createTextNode('Answer: '));
       var i = document.createElement('input');
       i.setAttribute('type', 'text');
       i.setAttribute('name', 'answer');
       i.setAttribute('id', 'kw-ans');
       as.appendChild(i);
       var s = document.createElement('input');
       s.setAttribute('type', 'submit');
       s.setAttribute('value', 'check!');
       addEvent(s, 'click', function(e) {
         if (!document.getElementById('kw-ans').value)
           e.preventDefault();
       });
       as.appendChild(s);
       var t = document.createElement('a');
       t.setAttribute('href', '#');
       addEvent(t, 'click', function(e) {
         document.getElementById('kwissle-alts').style['display'] = 'inline';
         document.getElementById('kwissle-answer').style['display'] = 'none';
         e.preventDefault();
       });
       t.appendChild(document.createTextNode('I don\'t know, show alternatives'));
       as.appendChild(t);
       a.appendChild(as);
       var bs = document.createElement('span');
       bs.setAttribute('id', 'kwissle-alts');
       bs.style['display'] = 'none';
       bs.appendChild(document.createTextNode('Alternatives: '));
       var b;
       for (var i = 0; i < response.alts.length; i++) {
         b = document.createElement('input');
         b.setAttribute('type', 'submit');
         b.setAttribute('name', 'alt_answer');
         b.setAttribute('value', response.alts[i]);
         bs.appendChild(b);
       }
       a.appendChild(bs);
       div.appendChild(a);
       div.style.display = 'block';
     }
  };
})();

function registerEventHandler(node, event, handler) {
  if (typeof node.addEventListener == 'function')
    node.addEventListener(event, handler, false);
  else
    node.attachEvent('on' + event, handler);
}

function addEvent( obj, type, fn ) {
  if ( obj.attachEvent ) {
    obj['e'+type+fn] = fn;
    obj[type+fn] = function(){obj['e'+type+fn]( window.event );}
    obj.attachEvent( 'on'+type, obj[type+fn] );
  } else
    obj.addEventListener( type, fn, false );
}
