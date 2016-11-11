post_encoded_token = function(url, fields) {
    var $form = $('<form action="'+url+'" method="post"></form>');
    var key, val;
    for(key in fields) {
        if(fields.hasOwnProperty(key)) {
            val = fields[key];
            $form.append('<input type="hidden" name="'+key+'" value="'+val+'" />');
        }
    }
    $form.submit();
}