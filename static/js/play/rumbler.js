var Rumbler = (function() {
   var _interval, _position, _xrel = 'left', _yrel = 'top';
   var _objXmove, _objYmove;

   function _rumble(elem, range) {
       _inner_rumble(elem, range, range, range);
   }
   function _inner_rumble(elem, rangeX, rangeY, rangeRot) {
      var randBool = Math.random();
      var randX = Math.floor(Math.random() * (rangeX + 1)) - rangeX / 2;
      var randY = Math.floor(Math.random() * (rangeY + 1)) - rangeY / 2;
      var randRot = Math.floor(Math.random() * (rangeRot + 1)) - rangeRot / 2;

      // IF INLINE, MAKE INLINE-BLOCK FOR ROTATION
      //---------------------------------
      // XXX Remove this for more speed?
      if (elem.css('display') === 'inline') {
	 inlineChange = true;
	 elem.css('display', 'inline-block');
      }

      // ENSURE MOVEMENT
      //---------------------------------
      if (randX === 0 && rangeX !== 0) {
	 if (randBool < .5) {
	    randX = 1;
	 }
	 else {
	    randX = -1;
	 }
      }

      if (randY === 0 && rangeY !== 0) {
	 if (randBool < .5) {
	    randY = 1;
	 }
	 else {
	    randY = -1;
	 }
      }

      // RUMBLE BASED ON POSITION
      //---------------------------------
      if (_position === 'absolute') {
	 elem.css({'position': 'absolute',
	           '-webkit-transform': 'rotate(' + randRot + 'deg)',
	           '-moz-transform': 'rotate(' + randRot + 'deg)',
	           '-o-transform': 'rotate(' + randRot + 'deg)',
	           'transform': 'rotate(' + randRot + 'deg)'});
	 elem.css(_xrel, _objXmove + randX + 'px');
	 elem.css(_yrel, _objYmove + randY + 'px');
      }
      if (_position === 'fixed') {
	 elem.css({'position': 'fixed',
	           '-webkit-transform': 'rotate(' + randRot + 'deg)',
	           '-moz-transform': 'rotate(' + randRot + 'deg)',
	           '-o-transform': 'rotate(' + randRot + 'deg)',
	           'transform': 'rotate(' + randRot + 'deg)'});
	 elem.css(_xrel, _objXmove + randX + 'px');
	 elem.css(_yrel, _objYmove + randY + 'px');
      }
      if (_position === 'static' || _position === 'relative') {
	 elem.css({'position': 'relative',
	           '-webkit-transform': 'rotate(' + randRot + 'deg)',
	           '-moz-transform': 'rotate(' + randRot + 'deg)',
	           '-o-transform': 'rotate(' + randRot + 'deg)',
	           'transform': 'rotate(' + randRot + 'deg)'});
	 elem.css(_xrel, randX + 'px');
	 elem.css(_yrel, randY + 'px');
      }

   }


   return {
      start: function(elem, speed, range) {
	 range = range != null ? range : 2;
	 if (_interval) {
	    clearInterval(_interval);
	 }

	 if (_xrel === 'left') {
	    _objXmove = parseInt(elem.css('left'), 10);
	 }
	 if (_xrel === 'right') {
	    _objXmove = parseInt(elem.css('right'), 10);
	 }
	 if (_yrel === 'top') {
	    _objYmove = parseInt(elem.css('top'), 10);
	 }
	 if (_yrel === 'bottom') {
	    _objYmove = parseInt(elem.css('bottom'), 10);
	 }

	 _elem = elem;
	 _position = elem.css('position');
	 _interval = setInterval(function() {
	    _rumble(_elem, range);
	 }, speed);
      },
      stop: function() {
	 clearInterval(_interval);
      }
   };

})();
