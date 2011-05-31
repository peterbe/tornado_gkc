soundManager.url = SOUND_CONFIG.url;
soundManager.onready(function(status) {
   if (status.success) {
      CONFIG.SOUNDS = {};
      soundManager.createSound('applause', SOUND_CONFIG.sounds.applause);
      CONFIG.SOUNDS['you_won'] = 'applause';
      soundManager.createSound('fake_applause', SOUND_CONFIG.sounds.fake_applause);
      CONFIG.SOUNDS['you_lost'] = 'fake_applause';
      soundManager.createSound('sword', SOUND_CONFIG.sounds.sword);
      CONFIG.SOUNDS['be_ready'] = 'sword';
      if (CONFIG.ENABLE_SOUNDS) {
         $('#sound-enabled').show();
      } else {
         $('#sound-disabled').show();
      }
      $('#sound-enabled').click(function() {
         CONFIG.ENABLE_SOUNDS = false;
         $(this).hide();
         $('#sound-disabled').show();
         $.post(SOUND_CONFIG.settings_toggle_url, {sound:'off'});
         return false;
      });
      $('#sound-disabled').click(function() {
         CONFIG.ENABLE_SOUNDS = true;
         $(this).hide();
         $('#sound-enabled').show();
         $.post(SOUND_CONFIG.settings_toggle_url, {sound:'on'});
         return false;
      });

   } else {
      CONFIG.ENABLE_SOUNDS = false;
      $('#sound-switch').hide();
   }
});
