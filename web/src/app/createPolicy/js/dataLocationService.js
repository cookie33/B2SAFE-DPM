dpmApp.service('dataLocation', function() {
    var locations = {source_systems:[],
        source_sites:[], source_resources:[],
        source_organisations:[],
        source_collections: [],
        target_collections: [],
        target_systems:[], target_sites:[],
        target_resources:[],
        target_organisations:[],
        location_types:[]};
    return {
        getLocations: function() {
            return locations;
        },
        setLocations: function(loc) {
            locations = loc;
        }
    };
});
