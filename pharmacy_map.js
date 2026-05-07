/**
 * MedGenius — Nearby Pharmacy Map (Leaflet + OpenStreetMap)
 * No API key required. Completely free.
 */

export class PharmacyMap {
  constructor(mapContainerId, listContainerId, options = {}) {
    this._mapEl  = document.getElementById(mapContainerId);
    this._listEl = document.getElementById(listContainerId);
    this._radius = options.radius || 2000;
    this._map    = null;
    this._markers = [];
    this._userMarker = null;
    this._userPos = null;
  }

  async init() {
    if (!this._mapEl) return;
    await this._loadLeaflet();
    this._setupMap();
    await this.locateUser();
  }

  _loadLeaflet() {
    return new Promise((resolve) => {
      if (window.L) { resolve(); return; }

      const link = document.createElement('link');
      link.rel  = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);

      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = resolve;
      document.head.appendChild(script);
    });
  }

  _setupMap() {
    this._map = L.map(this._mapEl).setView([20.5937, 78.9629], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(this._map);
  }

  async locateUser() {
    if (!navigator.geolocation) {
      this._showListMessage('Geolocation not supported in this browser.');
      return;
    }
    this._showListMessage('📍 Getting your location…');
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this._userPos = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          this._map.setView([this._userPos.lat, this._userPos.lng], 15);
          L.circleMarker([this._userPos.lat, this._userPos.lng], {
            radius: 10, fillColor: '#3b82f6', color: '#fff',
            weight: 3, opacity: 1, fillOpacity: 1,
          }).addTo(this._map).bindPopup('📍 Your Location').openPopup();
          resolve(this._userPos);
          this.findNearby();
        },
        (err) => {
          this._showListMessage('Could not get location. Please allow location access.');
          resolve(null);
        },
        { timeout: 10000, maximumAge: 60000 }
      );
    });
  }

  async findNearby() {
    if (!this._userPos) return;
    this._showListMessage('🔍 Searching for nearby pharmacies…');

    const { lat, lng } = this._userPos;
    const r = this._radius;

    const query = `
      [out:json][timeout:25];
      (
        node["amenity"="pharmacy"](around:${r},${lat},${lng});
        way["amenity"="pharmacy"](around:${r},${lat},${lng});
      );
      out center;
    `;

    try {
      const res  = await fetch('https://overpass-api.de/api/interpreter', {
        method: 'POST',
        body:   query,
      });
      const data = await res.json();
      this._displayResults(data.elements || []);
    } catch (e) {
      this._showListMessage('⚠️ Could not fetch pharmacy data. Check your internet connection.');
    }
  }

  _displayResults(places) {
    this._clearMarkers();

    if (!places.length) {
      this._showListMessage(`No pharmacies found within ${this._radius / 1000} km.`);
      return;
    }

    const withDist = places.map((p) => {
      const lat = p.lat || p.center?.lat;
      const lng = p.lon || p.center?.lon;
      return { p, lat, lng, dist: this._distanceKm(this._userPos, { lat, lng }) };
    }).filter(x => x.lat && x.lng).sort((a, b) => a.dist - b.dist).slice(0, 15);

    const listItems = [];

    withDist.forEach(({ p, lat, lng, dist }, i) => {
      const name    = p.tags?.name || 'Pharmacy';
      const address = [p.tags?.['addr:street'], p.tags?.['addr:city']].filter(Boolean).join(', ') || 'Address not available';
      const phone   = p.tags?.phone || p.tags?.['contact:phone'] || '';
      const open    = p.tags?.opening_hours || '';

      const marker = L.marker([lat, lng]).addTo(this._map);
      marker.bindPopup(`
        <div style="font-family:sans-serif;min-width:180px">
          <strong style="font-size:14px">${i + 1}. ${name}</strong><br>
          <span style="font-size:12px;color:#6b7280">${address}</span><br>
          ${phone ? `<span style="font-size:12px">📞 ${phone}</span><br>` : ''}
          ${open  ? `<span style="font-size:12px">🕐 ${open}</span><br>` : ''}
          <span style="font-size:12px;color:#3b82f6">${dist.toFixed(2)} km away</span><br>
          <a href="https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}"
             target="_blank" style="font-size:12px;color:#3b82f6">Get Directions ↗</a>
        </div>
      `);
      this._markers.push(marker);

      listItems.push(`
        <div class="ph-item" data-lat="${lat}" data-lng="${lng}"
             style="display:flex;gap:10px;align-items:flex-start;padding:10px 12px;
                    border-bottom:1px solid #f3f4f6;cursor:pointer;transition:background 0.15s;">
          <div style="min-width:24px;height:24px;border-radius:50%;background:#ef4444;
                      color:#fff;font-size:12px;font-weight:700;display:flex;
                      align-items:center;justify-content:center;">${i + 1}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:600;font-size:13px;color:#111827;white-space:nowrap;
                        overflow:hidden;text-overflow:ellipsis;">${name}</div>
            <div style="font-size:12px;color:#6b7280;margin-top:2px;">${address}</div>
            <div style="display:flex;gap:8px;margin-top:4px;align-items:center;flex-wrap:wrap;">
              <span style="font-size:12px;color:#3b82f6;">${dist.toFixed(2)} km</span>
              ${open ? `<span style="font-size:11px;color:#6b7280">${open}</span>` : ''}
              <a href="https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}"
                 target="_blank" rel="noopener"
                 style="font-size:11px;color:#3b82f6;"
                 onclick="event.stopPropagation()">Directions ↗</a>
            </div>
          </div>
        </div>
      `);
    });

    if (this._listEl) {
      this._listEl.innerHTML = `
        <h3 style="margin:0 0 10px;font-size:15px;font-weight:600;color:#111827;">
          Pharmacies within ${this._radius / 1000} km
          <span style="font-weight:400;color:#6b7280;font-size:13px;">(${withDist.length} found)</span>
        </h3>
        <div style="max-height:360px;overflow-y:auto;">${listItems.join('')}</div>
      `;

      this._listEl.querySelectorAll('.ph-item').forEach((el, i) => {
        el.addEventListener('click', () => {
          const marker = this._markers[i];
          if (marker) {
            this._map.setView(marker.getLatLng(), 17);
            marker.openPopup();
          }
        });
        el.addEventListener('mouseover', () => el.style.background = '#f9fafb');
        el.addEventListener('mouseleave', () => el.style.background = '');
      });
    }
  }

  _clearMarkers() {
    this._markers.forEach(m => this._map.removeLayer(m));
    this._markers = [];
  }

  _distanceKm(a, b) {
    const R    = 6371;
    const dLat = this._toRad(b.lat - a.lat);
    const dLng = this._toRad(b.lng - a.lng);
    const x    = Math.sin(dLat / 2) ** 2
               + Math.cos(this._toRad(a.lat)) * Math.cos(this._toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
  }

  _toRad(deg) { return deg * (Math.PI / 180); }

  _showListMessage(msg) {
    if (this._listEl) this._listEl.innerHTML = `<p style="font-size:13px;color:#6b7280;padding:12px 0;">${msg}</p>`;
  }
}