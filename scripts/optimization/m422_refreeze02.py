"""Versioned component after adding recorded per-transaction completion state."""
from m351_workflow import HERE,atomic
from m421_prepare import once
def main():
    s=(HERE/'m422_component_prepare.py').read_text(encoding='utf-8')
    s=once(s,'M422-borrowed-visual-component-01','M422-borrowed-visual-component-02')
    s=once(s,'tmp/m42201/component','tmp/m42202/component')
    s=once(s,'runs/M422-borrowed-component-01','runs/M422-borrowed-component-02')
    s=s.replace("'m422_component_prepare.py'","'m422_component_prepare02.py'")
    atomic(HERE/'m422_component_prepare02.py',s.encode('utf-8'),immutable=True)
    from m422_component_prepare02 import main as prepare
    prepare()
if __name__=='__main__':main()
