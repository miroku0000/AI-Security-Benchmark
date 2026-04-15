#if defined(__arm__) || defined(__thumb__)
static inline void set_msp(uint32_t top_of_stack) {
    __asm volatile ("msr msp, %0" :: "r" (top_of_stack) : );
}
static inline void disable_irq(void) {
    __asm volatile ("cpsid i" : : : "memory");
}
#define SCB_VTOR (*(volatile uint32_t *)0xE000ED08u)
static NORETURN void jump_to_application(uint32_t addr) {
    uint32_t msp = read_flash_u32(addr);
    uint32_t reset = read_flash_u32(addr + 4u);
    void (*entry)(void) = (void (*)(void))(uintptr_t)reset;
    platform_before_jump();
    disable_irq();
    SCB_VTOR = addr;
    set_msp(msp);
    entry();
    for (;;) {
    }
}
#else
static NORETURN void jump_to_application(uint32_t addr) {
    (void)addr;
    for (;;) {
    }
}
#endif