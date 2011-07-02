
head.ready(function() {
  $('form.image').submit(function() {
    var filename = $('input[type="file"]', this).val().toLowerCase();
    if (filename.search(/\.(png|jpg)$/gi) == -1) {
      //alert("File must be a .png, .jpg or .gif file");
      alert("File must be a .png or .jpg file");
      return false;
    }
    return true;
  });
});
