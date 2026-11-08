#import <Foundation/Foundation.h>

@interface MetricTrackerBridge : NSObject
@end

@implementation MetricTrackerBridge

// HAZARD 1: Objective-C +load executing synchronously before main()
+ (void)load {
    NSLog(@"MetricTrackerBridge pre-main load invoked");
}

@end
