#include <qemu-plugin.h>

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;

static uint64_t total, start, begin_pc, end_pc;
static unsigned interval;
static int active, failed;

static void begin(unsigned cpu, void *unused)
{
    (void)unused;
    if (cpu != 0U || active)
        failed = 1;
    start = total;
    active = 1;
}

static void end(unsigned cpu, void *unused)
{
    (void)unused;
    if (cpu != 0U || !active)
        failed = 1;
    fprintf(stderr, "{\"kind\":\"count\",\"interval\":%u,\"instructions\":%" PRIu64 "}\n",
            interval++, total - start);
    active = 0;
}

static void translate(qemu_plugin_id_t id, struct qemu_plugin_tb *tb)
{
    (void)id;
    for (size_t i = 0; i < qemu_plugin_tb_n_insns(tb); i++) {
        struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);
        uint64_t pc = qemu_plugin_insn_vaddr(insn);
        if (pc == begin_pc)
            qemu_plugin_register_vcpu_insn_exec_cb(insn, begin, QEMU_PLUGIN_CB_NO_REGS, NULL);
        else if (pc == end_pc)
            qemu_plugin_register_vcpu_insn_exec_cb(insn, end, QEMU_PLUGIN_CB_NO_REGS, NULL);
        qemu_plugin_register_vcpu_insn_exec_inline(insn, QEMU_PLUGIN_INLINE_ADD_U64, &total, 1);
    }
}

static void finish(qemu_plugin_id_t id, void *unused)
{
    (void)id;
    (void)unused;
    fprintf(stderr, "{\"kind\":\"counter_done\",\"intervals\":%u,\"failed\":%s}\n",
            interval, failed || active ? "true" : "false");
}

QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id, const qemu_info_t *info,
                                          int argc, char **argv)
{
    if (!info->system_emulation || strcmp(info->target_name, "arm") != 0 ||
        info->system.smp_vcpus != 1 || argc != 2)
        return -1;
    if (strncmp(argv[0], "begin=", 6) != 0 || strncmp(argv[1], "end=", 4) != 0)
        return -1;
    char *tail;
    begin_pc = strtoull(argv[0] + 6, &tail, 0);
    if (*tail != '\0')
        return -1;
    end_pc = strtoull(argv[1] + 4, &tail, 0);
    if (*tail != '\0' || begin_pc == end_pc || !begin_pc || !end_pc)
        return -1;
    qemu_plugin_register_vcpu_tb_trans_cb(id, translate);
    qemu_plugin_register_atexit_cb(id, finish, NULL);
    return 0;
}
