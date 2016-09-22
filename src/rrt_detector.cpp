#include "ros/ros.h"
#include "std_msgs/String.h"
#include <sstream>
#include <iostream>
#include <string>
#include <vector>
#include "stdint.h"
#include "functions.h"
#include "mtrand.h"


#include "nav_msgs/OccupancyGrid.h"
#include "std_msgs/Header.h"
#include "nav_msgs/MapMetaData.h"
#include "geometry_msgs/Point.h"
#include "visualization_msgs/Marker.h"
#include <tf/transform_listener.h>



// global variables
nav_msgs::OccupancyGrid mapData;
geometry_msgs::Point exploration_goal;
visualization_msgs::Marker points,line;
float xdim,ydim,resolution,Xstartx,Xstarty;

rdm r; // for genrating random numbers
//---------------------------------------
void mapCallBack(const nav_msgs::OccupancyGrid::ConstPtr& msg)
{ mapData=*msg;

}




int main(int argc, char **argv)
{

  unsigned long init[4] = {0x123, 0x234, 0x345, 0x456}, length = 4;
  MTRand_int32 irand(init, length); // 32-bit int generator
// this is an example of initializing by an array
// you may use MTRand(seed) with any 32bit integer
// as a seed for a simpler initialization
  MTRand drand; // double in [0, 1) generator, already init

// generate the same numbers as in the original C test program





  ros::init(argc, argv, "rrt_frontier_detector");
  ros::NodeHandle nh;
  
  // fetching all parameters
  float eta,init_map_x,init_map_y;
  
  ros::param::param<float>("eta", eta, 0.7);
  ros::param::param<float>("init_map_x", init_map_x, 20.0);
  ros::param::param<float>("init_map_y", init_map_y, 20.0);
 
  std::string ns;
  ns=ros::this_node::getNamespace();

  std::string temp ("map");
  std::string map_topic,base_frame_topic;
  ros::param::param<std::string>("map_topic", map_topic, ns+temp); 
  ros::param::param<std::string>("base_frame_topic", base_frame_topic, "robot_1/base_link");  // edit this  to after you finish>>>  "base_link" 
//---------------------------------------------------------------
ros::Subscriber sub= nh.subscribe("/robot_1/map", 100 ,mapCallBack);	

ros::Publisher targetspub = nh.advertise<geometry_msgs::Point>("/exploration_goals", 10);
//targetspub.publish(msg);

ros::Publisher pub = nh.advertise<visualization_msgs::Marker>("shapes", 10);
//targetspub.publish(msg);
  
  
ros::Rate rate(100); 
 
 
// wait until map is received, when a map is received, mapData.header.seq will not be < 1  
while (mapData.header.seq<1 or mapData.data.size()<1)  {  ros::spinOnce();  }


tf::TransformListener listener;
tf::StampedTransform transform;

listener.waitForTransform(mapData.header.frame_id, ns+base_frame_topic, ros::Time(0), ros::Duration(10.0) );
listener.lookupTransform(mapData.header.frame_id, ns+base_frame_topic, ros::Time(0), transform);

tf::Vector3 trans;

trans=transform.getOrigin();


std::vector< std::vector<float>  > V; 
std::vector<float> xnew; 


xnew.push_back( trans.x() );xnew.push_back( trans.y() );  
V.push_back(xnew);

//visualizations  points and lines..
points.header.frame_id=mapData.header.frame_id;
line.header.frame_id=mapData.header.frame_id;
points.header.stamp=ros::Time(0);
line.header.stamp=ros::Time(0);
	
points.ns=line.ns = "markers";
points.id = 0;
line.id =1;


points.type = points.POINTS;
line.type=line.LINE_LIST;

//Set the marker action.  Options are ADD, DELETE, and new in ROS Indigo: 3 (DELETEALL)
points.action =points.ADD;
line.action = line.ADD;
points.pose.orientation.w =1.0;
line.pose.orientation.w = 1.0;
line.scale.x =  0.06;
line.scale.y= 0.06;
points.scale.x=0.3; 
points.scale.y=0.3; 

line.color.r =0.0;//9.0/255.0
line.color.g= 0.0;//91.0/255.0
line.color.b =0.0;//236.0/255.0
points.color.r = 255.0/255.0;
points.color.g = 0.0/255.0;
points.color.b = 0.0/255.0;
points.color.a=1;
line.color.a = 1;//0.6;
points.lifetime = ros::Duration();
line.lifetime = ros::Duration();
	
  
geometry_msgs::Point p;  

p.x = trans.x() ;
p.y = trans.y() ;
p.z = 0;

points.points.push_back(p);


std::vector<float> frontiers;

xdim=mapData.info.width;
ydim=mapData.info.height;
resolution=mapData.info.resolution;
Xstartx=mapData.info.origin.position.x;
Xstarty=mapData.info.origin.position.y;

int i=0;


float xr,yr;
std::vector<float> x_rand,x_nearest,x_new;

while (ros::ok()){

// Sample free
x_rand.clear();
xr=(drand()*init_map_x)-(init_map_x*0.5);
yr=(drand()*init_map_y)-(init_map_y*0.5);//r.randomize()

x_rand.push_back( xr ); x_rand.push_back( yr );



// Nearest
x_nearest=Nearest(V,x_rand);

// Steer

x_new=Steer(x_nearest,x_rand,eta);
  		p.x=x_new[0]; 
		p.y=x_new[1]; 
		p.z=0.0;
          	points.points.push_back(p);
          	pub.publish(points) ;

// ObstacleFree    1:free     -1:unkown (frontier region)      0:obstacle
char   checking=ObstacleFree(x_nearest,x_new,mapData);

//ROS_INFO("%i",int(checking));

	  if (checking==-1){
          	
          	exploration_goal.x=x_new[0];
          	exploration_goal.y=x_new[1];
          	exploration_goal.z=0.0;
          	targetspub.publish(exploration_goal);
  		

          	listener.lookupTransform(mapData.header.frame_id, ns+base_frame_topic, ros::Time(0), transform);
          	trans=transform.getOrigin();
          	
	  	std::vector<float> x_init;
		
		x_init.push_back( trans.x() );x_init.push_back( trans.y() ); 
		
		V.clear();	
	
	  	V.push_back(x_init);
	  	
	  	points.points.clear();
	  	line.points.clear();
        	
        	}
	  	
	  
	  else if (checking==1){
	 	V.push_back(x_new);
	 	
	 	p.x=x_new[0]; 
		p.y=x_new[1]; 
		p.z=0.0;
	 	line.points.push_back(p);
	 	p.x=x_nearest[0]; 
		p.y=x_nearest[1]; 
		p.z=0.0;
	 	line.points.push_back(p);

	        }



pub.publish(line);  


   

ros::spinOnce();
rate.sleep();
  }return 0;}