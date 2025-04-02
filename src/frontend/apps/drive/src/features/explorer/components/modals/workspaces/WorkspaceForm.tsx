import { RhfTextarea } from "@/features/forms/components/RhfInput";

import { FormProvider } from "react-hook-form";

import { useTranslation } from "react-i18next";

import { Item } from "@/features/drivers/types";
import { SubmitHandler } from "react-hook-form";
import { useForm } from "react-hook-form";
import { RhfInput } from "@/features/forms/components/RhfInput";

export type WorkspaceFormInputs = {
  title: string;
  description: string;
};

export const WorkspaceForm = ({
  item,
  onSubmit,
}: {
  item?: Item;
  onSubmit: SubmitHandler<WorkspaceFormInputs>;
}) => {
  const { t } = useTranslation();
  const form = useForm<WorkspaceFormInputs>({
    defaultValues: {
      title: item?.title,
    },
  });

  const onSubmitWrapper: SubmitHandler<WorkspaceFormInputs> = async (data) => {
    form.reset();
    onSubmit(data);
  };

  return (
    <FormProvider {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmitWrapper)}
        id="workspace-form"
        className="mt-b"
      >
        <RhfInput
          label={t("explorer.actions.createWorkspace.modal.form.title")}
          fullWidth={true}
          autoFocus={true}
          {...form.register("title")}
        />
        <RhfTextarea
          label={t("explorer.actions.createWorkspace.modal.form.description")}
          fullWidth={true}
          className="mt-b"
          {...form.register("description")}
        />
      </form>
    </FormProvider>
  );
};
