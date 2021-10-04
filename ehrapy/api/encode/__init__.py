from typing import Dict, List, Optional, Union

from anndata import AnnData
from mudata import MuData
from rich import print
from rich.text import Text
from rich.tree import Tree

from ehrapy.api.encode.encode import Encoder


def encode(
    data: Union[AnnData, MuData],
    autodetect: Union[bool, Dict] = False,
    encodings: Union[Dict[str, Dict[str, List[str]]], Dict[str, List[str]]] = None,
) -> Optional[AnnData]:
    """Encode the initial read :class:`~anndata.AnnData or :class:`~mudata.MuData object. Categorical values could be either passed via parameters or autodetected.
    The categorical values are also stored in obs and uns (for keeping the original, unencoded values).
    The current encoding modes for each variable are also stored in uns (`current_encodings` key).
    Variable names in var are updated according to the encoding modes used.
    A variable name starting with `ehrapycat_` indicates an encoded column (or part of it).

    Available encodings are:
        1. one-hot encoding (https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html)
        2. label encoding (https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.LabelEncoder.html)
        3. count encoding (https://contrib.scikit-learn.org/category_encoders/count.html)

    Args:
        data: The initial :class:`~anndata.AnnData or :class:`~mudata.MuData object
        autodetect: Autodetection of categorical values
        encodings: Only needed if autodetect set to False (or False for some columns in case of a :class:`~mudata.MuData object).
        A dict containing the encoding mode and categorical name for the respective column (for each AnnData object in case of MuData object).

    Returns:
        An :class:`~anndata.AnnData` object with the encoded values in X or None (in case of :class:`~mudata.MuData object)

    Example:
        .. code-block:: python

            import ehrapy.api as ep
            adata = ep.io.read(...)
            # encode col1 and col2 using label encoding and encode col3 using one hot encoding
            adata_encoded = ep.encode.encode(adata, autodetect=False, {'label_encoding': ['col1', 'col2'], 'one_hot_encoding': ['col3']})
    """
    return Encoder.encode(data, autodetect, encodings)


def undo_encoding(
    adata: AnnData, columns: str = "all", from_cache_file: bool = False, cache_file: str = None
) -> AnnData:
    """Undo the current encodings applied to all columns in X. This currently resets the AnnData object to its initial state.
    Args:
        adata: The :class:`~anndata.AnnData object
        columns: The names of the columns to reset encoding for. Defaults to all columns.
        from_cache_file: Whether to reset all encodings by reading from a cached .h5ad file, if available.
        This resets the :class:`~anndata.AnnData object to its initial state.
        cache_file: The filename of the cache file to read from

    Returns:
        A (partially) encoding reset :class:`~anndata.AnnData object

    Example:
       .. code-block:: python

           import ehrapy.api as ep
           # adata_encoded is a encoded AnnData object
           adata_undone = ep.encode.undo_encoding(adata_encoded)
           # adata_undone is a fully reset AnnData object with no encodings
    """
    return Encoder.undo_encoding(adata, columns, from_cache_file, cache_file)


def type_overview(data: Union[MuData, AnnData], sort: bool = False, sort_reversed: bool = False) -> None:
    """Prints the current state of an :class:`~anndata.AnnData or :class:`~mudata.MuData object in a tree format.

    Args:
        data: :class:`~anndata.AnnData or :class:`~mudata.MuData object to display
        sort: Whether the tree output should be in sorted order
        sort_reversed: Whether to sort in reversed order or not
    """
    if isinstance(data, AnnData):
        _adata_type_overview(data, sort, sort_reversed)
    elif isinstance(data, MuData):
        _mudata_type_overview(data, sort, sort_reversed)
    else:
        print(f"[b red]Unable to present object of type {type(data)}. Can only display AnnData or Mudata objects!")
        raise EhrapyRepresentationError


def _adata_type_overview(adata: AnnData, sort: bool = False, sort_reversed: bool = False) -> None:
    """Display the :class:`~anndata.AnnData object in its current state (encoded and unencoded variables, obs)

    Args:
        adata: The :class:`~anndata.AnnData object to display
        sort: Whether to sort output or not
        sort_reversed: Whether to sort output in reversed order or not
    """
    encoding_mapping = {
        encoding: encoding.replace("encoding", "").replace("_", " ").strip() for encoding in Encoder.available_encodings
    }

    tree = Tree(
        f"[b green]Variable names for AnnData object with {len(adata.var_names)} vars and {len(adata.obs_names)} obs",
        guide_style="underline2 bright_blue",
    )
    if list(adata.obs.columns):
        branch = tree.add("Obs", style="b green")
        column_list = sorted(adata.obs.columns, reverse=sort_reversed) if sort else list(adata.obs.columns)
        for categorical in column_list:
            if "current_encodings" in adata.uns.keys():
                if categorical in adata.uns["current_encodings"].keys():
                    branch.add(
                        Text(
                            f"{categorical} 🔐; {len(adata.obs[categorical].unique())} different categories;"
                            f" currently {encoding_mapping[adata.uns['current_encodings'][categorical]]} encoded"
                        ),
                        style="blue",
                    )
                else:
                    branch.add(Text(f"{categorical}; moved from X to obs"), style="blue")
            else:
                branch.add(Text(f"{categorical}; moved from X to obs"), style="blue")

    branch_num = tree.add(Text("🔓 Unencoded variables"), style="b green")

    var_names = sorted(list(adata.var_names.values), reverse=sort_reversed) if sort else list(adata.var_names.values)
    for other_vars in var_names:
        idx = 0
        if not other_vars.startswith("ehrapycat"):
            branch_num.add(f"{other_vars}", style="blue")
        idx += 1

    if sort:
        print(
            "[b yellow]Displaying AnnData object in sorted mode. "
            "Note that this might not be the exact same order of the variables in X or var are stored!"
        )
    print(tree)


def _mudata_type_overview(mudata: AnnData, sort: bool = False, sort_reversed: bool = False) -> None:
    """Display the :class:`~mudata.MuData object in its current state (:class:`~anndata.AnnData objects with obs, shapes)

    Args:
        mudata: The :class:`~mudata.MuData object to display
        sort: Whether to sort output or not
        sort_reversed: Whether to sort output in reversed order or not
    """
    tree = Tree(
        f"[b green]Variable names for AnnData object with {len(mudata.var_names)} vars, {len(mudata.obs_names)} obs and {len(mudata.mod.keys())} modalities\n",
        guide_style="underline2 bright_blue",
    )

    modalities = sorted(list(mudata.mod.keys()), reverse=sort_reversed) if sort else list(mudata.mod.keys())
    for mod in modalities:
        branch = tree.add(
            f"[b green]{mod}: [not b blue]n_vars x n_obs: {mudata.mod[mod].n_vars} x {mudata.mod[mod].n_obs}"
        )
        branch.add(
            f"[blue]obs: [black]{', '.join(f'{_single_quote_string(col_name)}' for col_name in mudata.mod[mod].obs.columns)}"
        )
        branch.add(f"[blue]layers: [black]{', '.join(layer for layer in mudata.mod[mod].layers)}\n")
    print(tree)


def _single_quote_string(name: str) -> str:
    """Single quote a string to inject it into f-strings, since backslashes cannot be in double f-strings."""
    return f"'{name}'"


class EhrapyRepresentationError(ValueError):
    pass
