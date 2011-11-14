function loggedIn(response) {
  location.href = response.next_url;
}

function gotVerifiedEmail(assertion) {
  // got an assertion, now send it up to the server for verification
  if (assertion !== null) {
    $.ajax({
      type: 'POST',
      url: '/auth/login/browserid/',
      data: { assertion: assertion },
      success: function(res, status, xhr) {
        if (res === null) {}//loggedOut();
        else loggedIn(res);
      },
      error: function(res, status, xhr) {
        alert("login failure" + res);
      }
    });
  }
  else {
    //loggedOut();
  }
}

head.ready(function() {
  $('#browserid-signin').click(function() {
    navigator.id.getVerifiedEmail(gotVerifiedEmail);
    return false;
  });
});
