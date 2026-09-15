# NAO capability boundary

This area will contain NAO-specific capability contracts and target adapters.
The initial contracts are `Stand`, `Walk`, `Stop`, and `Observe`.

Capability invocation remains Agent-owned: a model or planner result does not
directly become a ROS 2 command.
