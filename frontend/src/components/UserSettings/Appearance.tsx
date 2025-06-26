import { Heading, Stack } from "@chakra-ui/react";
import { useTheme } from "next-themes";

import { Radio, RadioGroup } from "@/components/ui/radio";

const Appearance = () => {
  const { theme, setTheme } = useTheme();

  return (
    <>
      <Heading size="xl" pb={4}>
        Appearance
      </Heading>

      <RadioGroup
        onValueChange={(e) => setTheme(e.value)}
        value={theme}
        colorPalette="teal"
      >
        <Stack>
          <Radio value="system">System</Radio>
          <Radio value="light">Light Mode</Radio>
          <Radio value="dark">Dark Mode</Radio>
        </Stack>
      </RadioGroup>
    </>
  );
};
export default Appearance;
