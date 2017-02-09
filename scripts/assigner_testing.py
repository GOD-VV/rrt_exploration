#!/usr/bin/env python


#--------Include modules---------------
from copy import copy
import rospy
from visualization_msgs.msg import Marker
from std_msgs.msg import String
from geometry_msgs.msg import Point
from nav_msgs.msg import OccupancyGrid
import actionlib_msgs.msg
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from geometry_msgs.msg import PointStamped 
from geometry_msgs.msg import PoseStamped
from nav_msgs.srv import GetPlan
import actionlib
import tf



from time import time
from os import system
from random import random
from numpy import array,concatenate,vstack,delete,floor,ceil
from numpy import linalg as LA
from numpy import all as All
from numpy import inf
from functions import gridValue,robot,informationGain,discount,pathCost,unvalid
from sklearn.cluster import KMeans
from sklearn.cluster import MeanShift
import numpy as np
from numpy.linalg import norm

# Subscribers' callbacks------------------------------
mapData=OccupancyGrid()
frontiers=[]
global1=OccupancyGrid()
global2=OccupancyGrid()
global3=OccupancyGrid()
globalmaps=[]
def callBack(data):
	global frontiers,min_distance
	x=[array([data.point.x,data.point.y])]
	if len(frontiers)>0:
		frontiers=vstack((frontiers,x))
	else:
		frontiers=x
    

def mapCallBack(data):
    global mapData
    mapData=data

def globalMap(data):
    global global1,globalmaps
    global1=data
    indx=int(data._connection_header['topic'][7])-1
    globalmaps[indx]=data

# Node----------------------------------------------

def node():
	global frontiers,mapData,global1,global2,global3,globalmaps
	rospy.init_node('assigner', anonymous=False)
	
	# fetching all parameters
	map_topic= rospy.get_param('~map_topic','/robot_1/map')
	info_radius= rospy.get_param('~info_radius',1.0)					#this can be smaller than the laser scanner range, >> smaller >>less computation time>> too small is not good, info gain won't be accurate
	info_multiplier=rospy.get_param('~info_multiplier',3.0)		
	hysteresis_radius=rospy.get_param('~hysteresis_radius',3.0)			#at least as much as the laser scanner range
	hysteresis_gain=rospy.get_param('~hysteresis_gain',2.0)				#bigger than 1 (biase robot to continue exploring current region
	goals_topic= rospy.get_param('~goals_topic','/exploration_goals')	
	n_robots = rospy.get_param('~n_robots')
#	global_frame=rospy.get_param('~global_frame','/robot_1/map')

	rate = rospy.Rate(100)
#-------------------------------------------
	rospy.Subscriber(map_topic, OccupancyGrid, mapCallBack)
	rospy.Subscriber(goals_topic, PointStamped, callBack)
	pub = rospy.Publisher('frontiers', Marker, queue_size=10)
	pub2 = rospy.Publisher('centroids', Marker, queue_size=10)
#---------------------------------------------------------------------------------------------------------------
	

	for i in range(0,n_robots):
 		 globalmaps.append(OccupancyGrid()) 
 		 
 	for i in range(0,n_robots):
		rospy.Subscriber('/robot_'+str(i+1)+'/move_base_node/global_costmap/costmap', OccupancyGrid, globalMap) 
		
# wait if no frontier is received yet 
	while len(frontiers)<1:
		pass	
#wait if map is not received yet
	while (len(mapData.data)<1):
		pass
#wait if any of robots' global costmap map is not received yet
	for i in range(0,n_robots):
 		 while (len(globalmaps[i].data)<1):
 		 	pass
	
	global_frame="/"+mapData.header.frame_id


	rospy.loginfo("the map and global costmaps are received")
	
	points=Marker()
	points_clust=Marker()
#Set the frame ID and timestamp.  See the TF tutorials for information on these.
	points.header.frame_id= mapData.header.frame_id
	points.header.stamp= rospy.Time.now()

	points.ns= "markers2"
	points.id = 0
	
	points.type = Marker.POINTS
	
#Set the marker action for latched frontiers.  Options are ADD, DELETE, and new in ROS Indigo: 3 (DELETEALL)
	points.action = Marker.ADD;

	points.pose.orientation.w = 1.0

	points.scale.x=0.2
	points.scale.y=0.2 

	points.color.r = 255.0/255.0
	points.color.g = 255.0/255.0
	points.color.b = 0.0/255.0

	points.color.a=1;
	points.lifetime = rospy.Duration();

	p=Point()

	p.z = 0;

	pp=[]
	pl=[]
	
	points_clust.header.frame_id= "/robot_1/map"
	points_clust.header.stamp= rospy.Time.now()

	points_clust.ns= "markers3"
	points_clust.id = 4

	points_clust.type = Marker.POINTS

#Set the marker action for centroids.  Options are ADD, DELETE, and new in ROS Indigo: 3 (DELETEALL)
	points_clust.action = Marker.ADD;

	points_clust.pose.orientation.w = 1.0;

	points_clust.scale.x=0.2;
	points_clust.scale.y=0.2; 
	points_clust.color.r = 0.0/255.0
	points_clust.color.g = 255.0/255.0
	points_clust.color.b = 0.0/255.0

	points_clust.color.a=1;
	points_clust.lifetime = rospy.Duration();

	robots=[]
	for i in range(0,n_robots):
		robots.append(robot('/robot_'+str(i+1)))
	for i in range(0,n_robots):
		robots[i].sendGoal(robots[i].getPosition())
#-------------------------------------------------------------------------
#---------------------     Main   Loop     -------------------------------
#-------------------------------------------------------------------------
	while not rospy.is_shutdown():
#-------------------------------------------------------------------------	
#Clustering frontier points
		centroids=[]
		front=copy(frontiers)
		if len(front)>1:
			ms = MeanShift(bandwidth=0.3)   
			ms.fit(front)
			centroids= ms.cluster_centers_	 #centroids array is the centers of each cluster		

		#if there is only one frontier no need for clustering, i.e. centroids=frontiers
		if len(front)==1:
			centroids=front
			
		frontiers=copy(centroids)
			
		
		print "Number of centroids ",len(centroids)	
		
#-------------------------------------------------------------------------	
#clearing old frontiers  
      
		z=0
		while z<len(frontiers):
			threshold=0
			cond=False
			for i in range(0,n_robots):
				cond=(gridValue(globalmaps[i],frontiers[z])>threshold) or cond
				print "length glb cost  ",i,"  ",globalmaps[i].info.origin
					
			if (cond or (informationGain(mapData,[frontiers[z][0],frontiers[z][1]],info_radius))<1.0):
				frontiers=delete(frontiers, (z), axis=0)
				z=z-1
			z+=1
#-------------------------------------------------------------------------
#------------------------------------------------------------------------- 
#Plotting
		pp=[]	
		for q in range(0,len(frontiers)):
			p.x=frontiers[q][0]
			p.y=frontiers[q][1]
			pp.append(copy(p))
		points.points=pp
		pp=[]	
		for q in range(0,len(centroids)):
			p.x=centroids[q][0]
			p.y=centroids[q][1]
			pp.append(copy(p))
		points_clust.points=pp
			
		pub.publish(points)
		pub2.publish(points_clust) 
		rate.sleep()
#-------------------------------------------------------------------------

if __name__ == '__main__':
    try:
        node()
    except rospy.ROSInterruptException:
        pass
 
 
 
 