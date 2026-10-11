"""Keep unusual read plans visible; never turn them into a numerical verdict."""
def read_io_summary(events,expected_reads=648):
    reads=[r for r in events if r['name']=='weight_file_read']
    if not reads:raise ValueError('No recorded weight read')
    keys=('rchar','read_bytes','minflt','majflt');totals=dict.fromkeys(keys,0)
    for row in reads:
        if row['failed']:raise ValueError('Failed read interval')
        delta=row['metadata']['process_io_delta']
        for key in keys:
            value=delta[key]
            if isinstance(value,bool) or not isinstance(value,int) or value<0:
                raise ValueError('Invalid I/O counter delta')
            totals[key]+=value
    return dict(read_intervals=len(reads),read_process_io=totals,
        read_plan_status='EXPECTED_COUNT' if len(reads)==expected_reads else 'REQUIRES_PLAN_REVIEW',
        read_plan_accepted=len(reads)==expected_reads,
        note='Count mismatch is a diagnostic-plan review, not evidence of numerical failure or permission to promote performance.')
