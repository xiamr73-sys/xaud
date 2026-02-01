#ifndef __TIMER_H__
#define __TIMER_H__

#define TIM3_Fre                       (750000.0)                                // TIM0计数频率750KHz
//#define TIM4_Fre                       (3000.0)                                // TIM0计数频率750KHz
#define TIM4_Fre                       (6000.0)                                // TIM0计数频率750KHz

#define TIM3_FreH                       (0x000B)
#define TIM3_FreL                       (0x71B0)
/*************************************************************************************///External Function
extern void TIM1_HALL_Init(void);
extern void Timer2_Init(void);
extern void Timer2_QEP_Init(void);
extern void Timer3_Init(void);
extern void Timer4_Init(void);
extern void TIM4_Init_RF(void);

#endif
