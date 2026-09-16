"""Extract 12 financial fields from French annual filings, with provenance.

The package is organised in layers. A layer may only import from layers below it;
``tests/architecture/test_layer_dependencies.py`` enforces this.

    5  verify    checks and confidence aggregation
    4  units     EUR / kEUR resolution
    3  extract   extraction strategies      fields  declarative field catalogue
    2  routing   page classification
    1  text      line and number parsing    geometry  coordinate maths (pure)
    0  corpus    read-only access to data/

See wiki/06-plano/arquitetura-modular.md for the rationale.
"""

__version__ = "0.1.0"
