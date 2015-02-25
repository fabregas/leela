
angular.module("leela", []).
factory('leela', function($http) {
    return {
        get: function(resource, i_params) {
            return $http({method:'GET', url:'/api/'+resource, params: i_params});
        },
        post: function(resource, data) {
            return $http.post('/api/'+resource, data);
        },
        auth: function(login, password) {
            return $http.post('/api/__auth__', {username: login, password: password});
        },
        logout: function() {
            return $http.post('/api/__logout__');
        }
    };
});
