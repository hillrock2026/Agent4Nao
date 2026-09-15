# ROS 2 boundary

ROS 2 nodes, topics, services, and actions belong to Agent4NAO. This boundary
translates Agent4NAO capability requests into simulator or robot communication
and converts robot state into observations. Agent-Kernel must remain free of
ROS 2 dependencies.

The first implementation target is Gazebo Harmonic; a real-NAO adapter follows
the same capability contract later.
