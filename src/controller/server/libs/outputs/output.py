class Output:
    def __init__(self, device) -> None:
        self._device = device
        self._device_config = device.device_config

    def prepare_frame(self, frame):
        from libs.color_ranges import apply
        if not hasattr(self, '_color_range_device_id'):
            outputs = self._device.config.get('device_configs', {})
            key = next((key for key, value in outputs.items() if value is self._device_config), None)
            if key is None:
                matches = [key for key, value in outputs.items() if value == self._device_config]
                key = matches[0] if len(matches) == 1 else None
            self._color_range_device_id = key
        return apply(frame, self._color_range_device_id, self._device_config)

    @staticmethod
    def show(output_array) -> None:
        msg = f"Please implement this method. {output_array}"
        raise NotImplementedError(msg)
