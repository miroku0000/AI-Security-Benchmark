from pydantic import BaseModel, HttpUrl


class ScreenshotRequest(BaseModel):
    url: HttpUrl
