# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## Unreleased

## Added
- connect() now has a close_timeout parameter.

## Changed
- WebSocket objects will now close the socket automatically if an
    exception occurs in the event loop. Negating the need to use the
    websocket as a context manager.

## [0.1.7] - 2017-05-30

### Added
- Fully tested websockets functionality
- Documentation
