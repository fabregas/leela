Feature: Leela mgmt daemon

    Scenario: Default test config
        Given I create leela project "test_proj_1"
        When I start leela with "test" config as "user"
        Then I see leela nodaemon
        And I see "1" leela worker binded on "tcp" socket
        And get "/" with code "200"
        And contain "Available methods:" in "/api/__introspect__" body

    Scenario: Default production config noroot
        Given I create leela project "test_proj_2"
        When I start leela with "production" config as "user"
        Then I see leela failed with message "You need to have root privileges"

    Scenario: Default production config
        Given I create leela project "test_proj_3"
        When I start leela with "production" config as "superuser"
        Then I see leela daemon
        And I see "cpu_count" leela worker binded on "unix" socket
        And get "/" with code "200"
        And contain "Available methods:" in "/api/__introspect__" body
