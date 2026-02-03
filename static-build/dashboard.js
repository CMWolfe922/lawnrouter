/**
 * LawnRouter Dashboard - Mapbox Integration
 *
 * Provides map visualization with:
 * - Route line rendering
 * - Stop markers with profitability coloring
 * - Depot markers
 * - Stop highlighting and selection
 * - Live polling for route updates
 */

const DashboardMap = {
    map: null,
    selectedRouteId: null,
    selectedStopId: null,
    liveInterval: null,
    popup: null,

    /**
     * Initialize the Mapbox map
     * @param {string} token - Mapbox public access token
     * @param {string} style - Mapbox style URL
     */
    initMap(token, style) {
        if (!token) {
            console.warn('DashboardMap: No Mapbox token provided');
            this._updateStatus('Map unavailable - no token');
            return;
        }

        mapboxgl.accessToken = token;

        try {
            this.map = new mapboxgl.Map({
                container: 'map',
                style: style || 'mapbox://styles/mapbox/streets-v12',
                center: [-98.5795, 39.8283], // Center of US
                zoom: 4,
                attributionControl: true
            });

            // Add navigation controls
            this.map.addControl(new mapboxgl.NavigationControl(), 'top-right');

            this.map.on('load', () => {
                this._setupLayers();
                this._setupClickHandlers();
                this._updateStatus('Map ready - select a route to begin');
            });

            this.map.on('error', (e) => {
                console.error('Map error:', e);
                this._updateStatus('Map error occurred');
            });
        } catch (err) {
            console.error('Failed to initialize map:', err);
            this._updateStatus('Failed to initialize map');
        }
    },

    /**
     * Setup GeoJSON source and map layers
     */
    _setupLayers() {
        // Add empty GeoJSON source
        this.map.addSource('route-geojson', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        // Route line layer
        this.map.addLayer({
            id: 'route-line',
            type: 'line',
            source: 'route-geojson',
            filter: ['==', ['get', 'kind'], 'route_line'],
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': '#e94560',
                'line-width': 4,
                'line-opacity': 0.8
            }
        });

        // Route line outline for better visibility
        this.map.addLayer({
            id: 'route-line-outline',
            type: 'line',
            source: 'route-geojson',
            filter: ['==', ['get', 'kind'], 'route_line'],
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': '#000',
                'line-width': 6,
                'line-opacity': 0.3
            }
        }, 'route-line');

        // Stop circles with profitability colors
        this.map.addLayer({
            id: 'stop-circles',
            type: 'circle',
            source: 'route-geojson',
            filter: ['==', ['get', 'kind'], 'stop'],
            paint: {
                'circle-radius': 10,
                'circle-color': [
                    'case',
                    ['<', ['get', 'profit'], 0], '#ef4444',   // red - losing money
                    ['<', ['get', 'profit'], 10], '#facc15',  // yellow - low margin
                    '#4ade80'                                   // green - profitable
                ],
                'circle-stroke-width': 2,
                'circle-stroke-color': '#fff'
            }
        });

        // Depot circle (blue, larger)
        this.map.addLayer({
            id: 'depot-circle',
            type: 'circle',
            source: 'route-geojson',
            filter: ['==', ['get', 'kind'], 'depot'],
            paint: {
                'circle-radius': 12,
                'circle-color': '#3b82f6',
                'circle-stroke-width': 3,
                'circle-stroke-color': '#fff'
            }
        });

        // Stop highlight layer (ring around selected stop)
        this.map.addLayer({
            id: 'stop-highlight',
            type: 'circle',
            source: 'route-geojson',
            filter: ['==', ['get', 'location_id'], ''],
            paint: {
                'circle-radius': 16,
                'circle-color': 'transparent',
                'circle-stroke-width': 3,
                'circle-stroke-color': '#e94560'
            }
        });

        // Stop labels (order numbers)
        this.map.addLayer({
            id: 'stop-labels',
            type: 'symbol',
            source: 'route-geojson',
            filter: ['==', ['get', 'kind'], 'stop'],
            layout: {
                'text-field': ['get', 'order'],
                'text-size': 11,
                'text-font': ['DIN Pro Medium', 'Arial Unicode MS Bold'],
                'text-offset': [0, 0],
                'text-allow-overlap': true
            },
            paint: {
                'text-color': '#fff'
            }
        });

        // Depot label
        this.map.addLayer({
            id: 'depot-label',
            type: 'symbol',
            source: 'route-geojson',
            filter: ['==', ['get', 'kind'], 'depot'],
            layout: {
                'text-field': 'D',
                'text-size': 12,
                'text-font': ['DIN Pro Bold', 'Arial Unicode MS Bold'],
                'text-offset': [0, 0]
            },
            paint: {
                'text-color': '#fff'
            }
        });
    },

    /**
     * Setup click handlers for map interactions
     */
    _setupClickHandlers() {
        // Click on stop circle
        this.map.on('click', 'stop-circles', (e) => {
            e.preventDefault();
            const feature = e.features[0];
            const props = feature.properties;
            const locationId = props.location_id;

            // Show popup
            this._showStopPopup(e.lngLat, props);

            // Focus the stop
            this.focusStop(locationId);
        });

        // Click on depot
        this.map.on('click', 'depot-circle', (e) => {
            const feature = e.features[0];
            const props = feature.properties;

            if (this.popup) this.popup.remove();
            this.popup = new mapboxgl.Popup({ closeButton: true, closeOnClick: true })
                .setLngLat(e.lngLat)
                .setHTML(`
                    <div style="color: #333; padding: 4px;">
                        <strong style="color: #3b82f6;">Depot</strong><br>
                        <span>${props.name || 'Home Base'}</span><br>
                        <small style="color: #666;">${props.address || ''}</small>
                    </div>
                `)
                .addTo(this.map);
        });

        // Cursor changes on hover
        this.map.on('mouseenter', 'stop-circles', () => {
            this.map.getCanvas().style.cursor = 'pointer';
        });

        this.map.on('mouseleave', 'stop-circles', () => {
            this.map.getCanvas().style.cursor = '';
        });

        this.map.on('mouseenter', 'depot-circle', () => {
            this.map.getCanvas().style.cursor = 'pointer';
        });

        this.map.on('mouseleave', 'depot-circle', () => {
            this.map.getCanvas().style.cursor = '';
        });
    },

    /**
     * Show popup for a stop with revenue/profit info
     */
    _showStopPopup(lngLat, props) {
        if (this.popup) this.popup.remove();

        const profitColor = props.profit < 0 ? '#ef4444' : props.profit < 10 ? '#facc15' : '#4ade80';

        this.popup = new mapboxgl.Popup({ closeButton: true, closeOnClick: true })
            .setLngLat(lngLat)
            .setHTML(`
                <div style="color: #333; padding: 4px; min-width: 120px;">
                    <strong style="color: #e94560;">Stop #${props.order}</strong><br>
                    <div style="margin-top: 4px;">
                        <span>Revenue:</span> <strong>$${props.revenue}</strong><br>
                        <span>Profit:</span> <strong style="color: ${profitColor}">$${parseFloat(props.profit).toFixed(2)}</strong><br>
                        <span>Service:</span> ${props.service_minutes} min
                    </div>
                </div>
            `)
            .addTo(this.map);
    },

    /**
     * Load and display route GeoJSON data
     * @param {string} routeId - UUID of the route to load
     */
    async loadRoute(routeId) {
        if (!routeId) {
            this._updateStatus('No route ID provided');
            return;
        }

        this.selectedRouteId = routeId;
        this._updateStatus('Loading route...');

        try {
            const response = await fetch(`/dashboard/api/route-geojson?route_id=${routeId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const geojson = await response.json();

            // Update source data
            const source = this.map.getSource('route-geojson');
            if (source) {
                source.setData(geojson);
            }

            // Count stops
            const stopCount = geojson.features.filter(f => f.properties.kind === 'stop').length;

            // Fit bounds to route line
            const routeLine = geojson.features.find(f => f.properties.kind === 'route_line');
            if (routeLine && routeLine.geometry.coordinates.length > 0) {
                const bounds = new mapboxgl.LngLatBounds();
                routeLine.geometry.coordinates.forEach(coord => bounds.extend(coord));
                this.map.fitBounds(bounds, {
                    padding: { top: 50, bottom: 50, left: 50, right: 50 },
                    maxZoom: 15
                });
            }

            this._updateStatus(`Route loaded: ${stopCount} stops`);
        } catch (err) {
            console.error('Error loading route:', err);
            this._updateStatus(`Error: ${err.message}`);
        }
    },

    /**
     * Focus on a specific stop (highlight and pan)
     * @param {string} locationId - UUID of the location to focus
     */
    focusStop(locationId) {
        if (!locationId) return;

        this.selectedStopId = locationId;

        // Update highlight filter
        this.map.setFilter('stop-highlight', ['==', ['get', 'location_id'], locationId]);

        // Find the feature and pan to it
        const source = this.map.getSource('route-geojson');
        if (source && source._data) {
            const feature = source._data.features.find(
                f => f.properties.location_id === locationId
            );
            if (feature && feature.geometry.type === 'Point') {
                this.map.flyTo({
                    center: feature.geometry.coordinates,
                    zoom: 16,
                    duration: 1000
                });
            }
        }

        // Load customer card via HTMX
        if (typeof htmx !== 'undefined') {
            htmx.ajax('GET', `/dashboard/partials/customer-card?location_id=${locationId}`, '#customerCard');
        }

        // Load pricing after small delay (let customer card load first)
        setTimeout(() => this._loadPricing(locationId), 100);

        // Highlight table row
        this._highlightTableRow(locationId);
    },

    /**
     * Highlight the corresponding row in the stops table
     */
    _highlightTableRow(locationId) {
        const routeDetailEl = document.getElementById('routeDetail');
        if (!routeDetailEl) return;

        routeDetailEl.querySelectorAll('tr').forEach(row => {
            row.classList.remove('selected');
            if (row.dataset && row.dataset.locationId === locationId) {
                row.classList.add('selected');
                // Scroll row into view if needed
                row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        });
    },

    /**
     * Load pricing data for a stop
     */
    async _loadPricing(locationId) {
        const pricingBox = document.getElementById('pricingBox');
        if (!pricingBox) return;

        if (!this.selectedRouteId) {
            pricingBox.innerHTML = '<p class="empty-state">Select a route first</p>';
            return;
        }

        pricingBox.innerHTML = '<div class="spinner"></div> Loading pricing...';

        try {
            const url = `/dashboard/api/stop-pricing?route_id=${this.selectedRouteId}&location_id=${locationId}&target_margin=0.30`;
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Determine profit color
            const profit = parseFloat(data.profit);
            const profitClass = profit < 0 ? 'text-danger' : profit < 10 ? 'text-warning' : 'text-success';

            pricingBox.innerHTML = `
                <div class="pricing-row">
                    <span>Revenue:</span>
                    <span>$${data.revenue}</span>
                </div>
                <div class="pricing-row">
                    <span>Cost:</span>
                    <span>$${data.cost}</span>
                </div>
                <div class="pricing-row">
                    <span>Profit:</span>
                    <span class="${profitClass}">$${data.profit}</span>
                </div>
                <div class="pricing-row">
                    <span>Margin:</span>
                    <span>${data.margin.toFixed(1)}%</span>
                </div>
                <div class="suggested-price">
                    Suggested: $${data.suggested_price}
                </div>
            `;
        } catch (err) {
            console.error('Error loading pricing:', err);
            pricingBox.innerHTML = '<p class="empty-state">Error loading pricing</p>';
        }
    },

    /**
     * Start live polling to refresh route data
     * @param {number} seconds - Polling interval in seconds
     */
    startLivePolling(seconds = 15) {
        this.stopLivePolling();

        if (!this.selectedRouteId) {
            this._updateStatus('Select a route first to enable live updates');
            return;
        }

        this._updateStatus(`Live polling active (every ${seconds}s)`);

        // Initial load
        this.loadRoute(this.selectedRouteId);

        // Set interval
        this.liveInterval = setInterval(() => {
            if (this.selectedRouteId) {
                this.loadRoute(this.selectedRouteId);
            }
        }, seconds * 1000);
    },

    /**
     * Stop live polling
     */
    stopLivePolling() {
        if (this.liveInterval) {
            clearInterval(this.liveInterval);
            this.liveInterval = null;
            this._updateStatus('Live polling stopped');
        }
    },

    /**
     * Update status text display
     */
    _updateStatus(msg) {
        const el = document.getElementById('mapStatus');
        if (el) {
            el.textContent = msg;
        }
    },

    /**
     * Clear all map data
     */
    clearMap() {
        const source = this.map.getSource('route-geojson');
        if (source) {
            source.setData({ type: 'FeatureCollection', features: [] });
        }
        this.selectedRouteId = null;
        this.selectedStopId = null;
        this.stopLivePolling();
        this._updateStatus('Map cleared');
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.__MAPBOX_PUBLIC_TOKEN__) {
        DashboardMap.initMap(window.__MAPBOX_PUBLIC_TOKEN__, window.__MAP_STYLE__);
    }
});

// Export for global access
window.DashboardMap = DashboardMap;
