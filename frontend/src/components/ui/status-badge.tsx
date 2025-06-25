import { Badge, HStack, Spinner, Text } from "@chakra-ui/react";

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const getStatusConfig = () => {
    switch (status) {
      case "pending":
        return { icon: "⏳", color: "gray", text: "Waiting" };
      case "processing":
        return {
          icon: <Spinner size="xs" />,
          color: "blue",
          text: "Processing",
        };
      case "completed":
        return { icon: "✅", color: "green", text: "Completed" };
      case "failed":
        return { icon: "❌", color: "red", text: "Failed" };
      default:
        return { icon: "❓", color: "gray", text: "Unknown" };
    }
  };

  const config = getStatusConfig();

  return (
    <Badge variant="outline" colorScheme={config.color}>
      <HStack gap={1} align="center">
        {typeof config.icon === "string" ? (
          <Text fontSize="xs">{config.icon}</Text>
        ) : (
          config.icon
        )}
        <Text>{config.text}</Text>
      </HStack>
    </Badge>
  );
}
