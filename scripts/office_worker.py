"""Run only isolated Office instances owned by this conversion job."""
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--kind", choices=["word", "excel", "powerpoint"], required=True)
    args = parser.parse_args()
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    app = document = None
    source, output = str(Path(args.input).resolve()), str(Path(args.output).resolve())
    target = Path(output).suffix.lstrip(".")
    try:
        app = win32com.client.DispatchEx({"word": "Word.Application", "excel": "Excel.Application",
                                        "powerpoint": "PowerPoint.Application"}[args.kind])
        app.AutomationSecurity = 3
        if args.kind == "word":
            app.Visible = False
            app.DisplayAlerts = 0
            document = app.Documents.Open(FileName=source, ReadOnly=True, AddToRecentFiles=False,
                                           ConfirmConversions=False, PasswordDocument="converter-no-password")
            if target == "pdf":
                document.ExportAsFixedFormat(OutputFileName=output, ExportFormat=17)
            else:
                document.SaveAs2(FileName=output, FileFormat={"doc": 0, "docx": 16, "odt": 23,
                                                            "rtf": 6, "html": 10, "txt": 7}[target], Encoding=65001)
        elif args.kind == "excel":
            app.Visible = False
            app.DisplayAlerts = False
            app.AskToUpdateLinks = False
            document = app.Workbooks.Open(source, UpdateLinks=0, ReadOnly=True,
                                           Password="converter-no-password", IgnoreReadOnlyRecommended=True,
                                           AddToMru=False)
            if target == "pdf":
                document.ExportAsFixedFormat(0, output)
            else:
                document.SaveAs(output, FileFormat={"xls": 56, "xlsx": 51, "ods": 60}[target])
        else:
            app.DisplayAlerts = 1
            document = app.Presentations.Open(source, ReadOnly=True, Untitled=False, WithWindow=False)
            if target == "pdf":
                document.SaveAs(output, 32)
            else:
                document.SaveAs(output, {"ppt": 1, "pptx": 24, "odp": 35}[target])
        return 0
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        try:
            if document is not None:
                if args.kind == "word":
                    document.Close(SaveChanges=0)
                elif args.kind == "excel":
                    document.Close(SaveChanges=False)
                else:
                    document.Close()
        finally:
            if app is not None:
                collection = {"word": "Documents", "excel": "Workbooks", "powerpoint": "Presentations"}[args.kind]
                if getattr(app, collection).Count == 0:
                    app.Quit()
            pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
