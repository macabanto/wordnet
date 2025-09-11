README

pseudocode
Core Data Structures
•	nodeObjects[] - array of clickable node sprites
•	nodeGroup - Three.js group containing all text sprites
•	linkGroup - Three.js group containing all connection lines
•	centeredNode - currently focused node
•	visited - set of already-fetched term IDs

Data Flow
•	App starts → fetch initial term by hardcoded ID
•	initializeGraph() creates visual layout
•	User clicks node → refocusToNode() animates transition
•	loadTermById() fetches new data using clicked node's ID
•	expandFromNode() shows new connections
•	Repeat from User cicks node

Scene Setup
•	INITIALIZE scene, camera, renderer, raycaster, mouse with Three.js 
•	SET camera position to (0, 0, 300) 
•	CREATE raycaster for mouse interaction 
•	CREATE groups for nodes and links 
•	ADD resize listener for responsive design

Key Functions
createTextSprite(text, color)
•	PURPOSE: Generate text sprites for 3D display
•	PROCESS:
o	Create HTML5 canvas
o	Draw text with styling (font, shadow, color)
o	Convert canvas to Three.js texture
o	Create sprite with texture
o	Scale appropriately (larger for center terms)
•	RETURN: Three.js Sprite object
initializeGraph(termData)
•	PURPOSE: Create initial graph layout from term data
•	PROCESS:
o	Clear existing nodes and links (memory cleanup)
o	Create center term sprite at origin (0,0,0)
o	FOR each synonym in termData.linked_synonyms:
	Create sprite at position (x,y,z)
	Store metadata (id, term, line reference)
	Create connecting line to center
	Add to nodeObjects for interaction
o	Add all sprites to nodeGroup

refocusToNode(clickedNode)
•	PURPOSE: Smoothly transition focus to clicked node
•	PROCESS:
o	Calculate group position to center clicked node at origin
o	Animate all other nodes collapsing into original center
o	Animate group position change over 1000ms
o	Clean up collapsed nodes and their connections
o	Set clicked node as new center
•	RETURN: Promise that resolves when animation complete

expandFromNode(centerNode, termDoc)
•	PURPOSE: Show new synonyms radiating from focused node
•	PROCESS:
o	Clear nodeObjects (reset clickable nodes)
o	FOR each synonym in termDoc.linked_synonyms:
	Create sprite starting at center position, scale 0
	Animate outward to final position (x,y,z)
	 Animate scale from 0 to full size
	Create and animate connecting line
o	Stagger animations with random delays (900-1100ms)

loadTermById(id)
•	PURPOSE: Fetch term data from server API
•	PROCESS:
o	Make HTTP GET request to `/api/term/${id}`
o	Check response status
o	Parse JSON response
•	RETURN: Promise with term data

Mouse Interaction System
•	mousedown:
o	SET isDragging = true
o	SET clickCandidate = true (potential click)
o	STORE mouse position
o	RESET rotation velocity
•	mousemove:
o	IF movement > 5px threshold: clickCandidate = false
o	UPDATE mouse coordinates for raycaster
o	IF dragging: UPDATE rotation and velocity
•	mouseup:
o	IF not clickCandidate: RETURN (was drag, not click)
o	USE raycaster to find intersected objects
o	IF node clicked and not already centered:
o	CALL refocusToNode() then expandFromNode()

Animation Loop
•	animate():
o	REQUEST next animation frame
o	IF not dragging:
	APPLY rotation velocity with inertia decay
o	UPDATE scene rotation
o	RENDER scene

Shell commands :
assuming db is already populated...
 * setup tunnel ( detached ) - "nohup cloudflared tunnel --config ~/.cloudflared/config.yml run synonym-api > tunnel.log 2>&1 &"
 * build dist - "npm run build"
 * deploy dist - "npm run deploy"
 * run server ( detached ) - "nohup node server.js > server.log 2>&1 &"
 * check server "ps aux | grep node"