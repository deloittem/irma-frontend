'use strict';

(function () {

  var dependencies = ['$rootScope', '$route'];
  var State = function ($rootScope, $route) {

    // Initialize controller
    for (var i = 0; i < dependencies.length; i++){ this[dependencies[i]] = arguments[i];}

    this.location = undefined;
    this.currentScan = undefined;
    this.settings = undefined;
    this.baseResults = {};
    this.results = {}

    this.initResults = function(settings){
      if(!this.currentScan) { return false;}
      else {
        for(var i=0; i<settings.probes.length; i++){
          if(settings.probes[i].active){ this.baseResults[settings.probes[i].name] = {result: '__loading__'}; }
        }
      }
    };

    this.upgradeResults = function(files){
      for(var name in files){ files[name].results = angular.copy(this.baseResults);}
      this.results  = files;
    };

    $rootScope.state = this;
    $rootScope.$on('$routeChangeSuccess', function(event, newRoute, oldRoute){
      this.location = newRoute.location;
    }.bind(this));
  };

  State.$inject = dependencies;
  angular.module('irma').service('state', State);
}());