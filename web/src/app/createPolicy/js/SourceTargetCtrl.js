function sourceTargetCtrl($scope, $http, $injector, policy, disabled_flags,
        data_location, submitFlag) {
    $scope.policy = policy;
    $injector.invoke(dpmCtrl, this, {$scope: $scope});
    var disabled_flags_obj = disabled_flags.getFlags();
    var loc_obj = data_location.getLocations();

    $scope.src_systems = loc_obj.source_systems;
    $scope.tgt_systems = loc_obj.target_systems;
    $scope.src_sites = loc_obj.source_sites;
    $scope.tgt_sites = loc_obj.target_sites;
    $scope.src_resources = loc_obj.source_resources;
    $scope.tgt_resources = loc_obj.target_resources;
    $scope.src_site_disabled = disabled_flags_obj.source_site;
    $scope.tgt_site_disabled = disabled_flags_obj.target_site;
    $scope.src_resource_disabled = disabled_flags_obj.source_resource;
    $scope.tgt_resource_disabled = disabled_flags_obj.target_resource;
    $scope.tgt_system_disabled = disabled_flags_obj.tgt_system;
    $scope.tgt_loc_type_disabled = disabled_flags_obj.tgt_loc_type;

    // Read from the database the available locations
    $scope.changeLocation = function() {
        var get_locations = $http({method: 'GET',
            url: '${CGI_URL}/query_actions.py',
            params: {qtype: 'locations',
                 operation: $scope.policy.action.name,
                 type: $scope.policy.type.name,
                 trigger: $scope.policy.trigger.name} });
        get_locations.then(function(results) {
            var data = results.data;
            loc_obj.location_types = [];
            for (var idx = 0; idx < data.length; ++idx) {
                if (data[idx].length > 0) {
                    loc_obj.location_types =
                        storeData(loc_obj.location_types, data[idx][0]);
                }
            }
            $scope.location_types = loc_obj.location_types;
            data_location.setLocations(loc_obj);
            disabled_flags_obj.tgt_loc_type = false;
            disabled_flags.setFlags(disabled_flags_obj);
            $scope.pristineFlags.target.organisation = false;
            $scope.policy.target.loctype.name = "--- Select a Location Type ---";
            $scope.tgt_loc_type_disabled = disabled_flags_obj.tgt_loc_type;

        });
    };


    // Read from the database the available systems
    $scope.changeSystem = function() {
        var get_systems = $http({method: "GET",
            url: "${CGI_URL}/query_resource.py",
            params: {qtype: "systems"}});

        get_systems.then(function(results) {
            var data = results.data;
            loc_obj.source_systems = [];
            loc_obj.target_systems = [];
            for (var idx = 0; idx < data.length; ++idx) {
                if (data[idx].length > 0) {
                    loc_obj.source_systems =
                        storeData(loc_obj.source_systems, data[idx][0]);
                    loc_obj.target_systems =
                        storeData(loc_obj.target_systems, data[idx][0]);
                }
            }
            $scope.src_systems = loc_obj.source_systems;
            $scope.tgt_systems = loc_obj.target_systems;
            data_location.setLocations(loc_obj);
            disabled_flags_obj.tgt_system = false;
            disabled_flags.setFlags(disabled_flags_obj);
            $scope.pristineFlags.target.location_type = false;
            $scope.policy.target.system.name = "--- Select a System ---";
            $scope.tgt_system_disabled = disabled_flags_obj.tgt_system;
        });
    };

    // Once the system has been selected populate the sites list for the
    // source
    $scope.changeSrcSite = function() {
        var get_sites = $http({method: "GET",
            url: "${CGI_URL}/query_resource.py",
            params: {qtype: "sites",
                system: $scope.policy.source.system.name}});

        get_sites.then(function(results) {
            var data = results.data;
            loc_obj.source_sites = [];
            for (var idx = 0; idx < data.length; ++idx) {
                if (data[idx].length > 0) {
                    loc_obj.source_sites =
                        storeData(loc_obj.source_sites, data[idx][0]);
                }
            }
            $scope.src_sites = loc_obj.source_sites;
            data_location.setLocations(loc_obj);
        });
        disabled_flags_obj.source_site = false;
        disabled_flags.setFlags(disabled_flags_obj);
        $scope.policy.source.site.name = "--- Select a Site ---";
        $scope.src_site_disabled = disabled_flags_obj.source_site;
    };

    // Once the system has been selected populate the sites list
    $scope.changeTgtSite = function() {
        var get_tgtsites = $http({method: "GET",
            url: "${CGI_URL}/query_resource.py",
            params: {qtype: "sites",
                system: $scope.policy.target.system.name} });
        get_tgtsites.then(function(results) {
            var data = results.data;
            loc_obj.target_sites = [];
            for (var idx = 0; idx < data.length; ++idx) {
                if (data[idx].length > 0) {
                    $scope.tgt_sites =
                        storeData(loc_obj.target_sites, data[idx][0]);
                }
            }
        });
        disabled_flags_obj.target_site = false;
        disabled_flags.setFlags(disabled_flags_obj);
        $scope.policy.target.site.name = "--- Select a Site ---";
        $scope.pristineFlags.target.system = false;
        $scope.tgt_site_disabled = disabled_flags_obj.target_site;
    };

    // Once the site has been selected populate the source resources list
    $scope.changeSrcResource = function() {
        var get_resources = $http({method: "GET",
            url: "${CGI_URL}/query_resource.py",
            params: {qtype: "resources",
                system: $scope.policy.source.system.name,
                site: $scope.policy.source.site.name} });
        get_resources.then(function(results) {
            var data = results.data;
            loc_obj.source_resources = [];
            loc_obj.source_paths = [];
            for (var idx = 0; idx < data.length; ++idx) {
                if (data[idx].length > 0) {
                    $scope.src_resources =
                        storeData(loc_obj.source_resources, data[idx][0]);
                    $scope.src_paths =
                        storeData(loc_obj.source_paths, data[idx][1]);
                }
            }
        });
        disabled_flags_obj.source_resource = false;
        disabled_flags.setFlags(disabled_flags_obj);
        $scope.policy.source.resource.name = "--- Select a Resource ---";
        $scope.src_resource_disabled = disabled_flags_obj.source_resource;
    };

    // Once the site has been selected populate the resources list
    $scope.changeTgtResource = function() {
        var get_tgtresources = $http({method: "GET",
            url: "${CGI_URL}/query_resource.py",
            params: {qtype: "resources",
            system: $scope.policy.target.system.name,
            site: $scope.policy.target.site.name} });
        get_tgtresources.then(function(results) {
            var data = results.data;
            loc_obj.target_resources = [];
            loc_obj.target_paths = [];
            for (var idx = 0; idx < data.length; ++idx) {
                if (data[idx].length > 0) {
                    $scope.tgt_resources =
                        storeData(loc_obj.target_resources, data[idx][0]);
                    $scope.tgt_paths = storeData(loc_obj.target_paths,
                        data[idx][1]);
                }
            }
        });
        disabled_flags_obj.target_resource = false;
        disabled_flags.setFlags(disabled_flags_obj);
        $scope.pristineFlags.target.site = false;
        $scope.policy.target.resource.name = "--- Select a Resource ---";
        $scope.tgt_resource_disabled = disabled_flags_obj.target_resource;

    };

    // Function to update the pristine flag (we need this as the state
    // is not presered when we go back a page)
    $scope.updateTgtResource = function() {
      console.log("update called! target " + $scope.policy.target.resource);
      console.log("update called! source " + $scope.policy.source.resource);
      var idx = $scope.tgt_resources.indexOf($scope.policy.target.resource);
      if (idx < 0) {
        idx = $scope.src_resources.indexOf($scope.policy.source.resource);
      }
      console.log("idx is " + idx);
      $scope.policy.target.path = $scope.tgt_paths[idx].name;
      console.log("target path is " + $scope.target_path);
      $scope.pristineFlags.target.resource = false;
    };
}
