private var html: String {
        """
        <!doctype html>
        <html>
        <head>
          <meta name="viewport" content="initial-scale=1.0, width=device-width, user-scalable=no" />
          <style>
            html, body, #map {
              margin: 0;
              padding: 0;
              width: 100%;
              height: 100%;
              background: #f4f4f4;
            }
          </style>
          <script src="https://maps.googleapis.com/maps/api/js?key=\(escaped(apiKey))"></script>
          <script>
            function init() {
              const center = { lat: \(latitude), lng: \(longitude) };
              const map = new google.maps.Map(document.getElementById('map'), {
                center: center,
                zoom: \(zoom),
                mapTypeControl: false,
                streetViewControl: false,
                fullscreenControl: false
              });