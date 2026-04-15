function focusLocation(lat, lng, title) {
              if (!map) { return; }
              const point = { lat: lat, lng: lng };
              map.panTo(point);
              map.setZoom(12);
              if (activeMarker) {
                activeMarker.setMap(null);
              }
              activeMarker = new google.maps.Marker({
                position: point,
                map,
                title: title,
                icon: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png"
              });
            }